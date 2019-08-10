import argparse
import asyncio
import logging
import signal
import sys
import os

from enum import Enum
from dataclasses import dataclass, field
from typing import Union, Tuple

import aiokatcp

from aiohttp import web
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from prometheus_async import aio

WORKAROUND_STRING_ADDRESS = False
STRING_ADDRESS_TYPES = ['string', 'address']


@dataclass
class SensorMetric:
    """SensorMetric class formats a `aiokatcp.sensor.Sensor` into a Prometheus
       compatible metric.

       If `WORKAROUND_STRING_ADDRESS`, is enabled a list of sensor values for
       katcp types `address` and `string` is stored (as they are received) and the index
       into that list is returned. A user may be able to infer the meaning behind the
       index.
    """

    sensor: aiokatcp.sensor.Sensor
    saved_values: list = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        """If the `aiokatcp.sensor.Sensor` is `enum` then the options are stored. The
           list is also the the `HELP` string.

        Returns
        -------
        None
        """
        if self.sensor.type_name == 'discrete':
            self.saved_values = self.sensor.params
        if not WORKAROUND_STRING_ADDRESS and (self.sensor.type_name in
                                              STRING_ADDRESS_TYPES):
            assert 0, "WORKAROUND_STRING_ADDRESS is disabled"

    @property
    def metric_name(self) -> str:
        """Updates sensor name to a Promtheus valid value.

        Returns
        -------
        str
            Prometheus valid sensor name.
        """
        return self.sensor.name.replace(".", "__").replace("-", "_")

    def update_sensor(self) -> None:
        """Add the string value to the saved entries for this sensor if
           `STRING_ADDRESS_TYPES` is enabled.

        Returns
        -------
        None
        """
        if self.sensor.type_name in STRING_ADDRESS_TYPES:
            if self.sensor.value not in self.saved_values:
                self.saved_values.append(self.sensor.value)

    @property
    def metric_value(self) -> Union[int, float]:
        """Returns the sensort value as a valid Prometheus entry.

        Returns
        -------
        Union[int, float]
            - If the sensor is `string`, `address` or `discrete` return an index into
              the stored values.
            - If not then return the sensor value.
        """
        if self.sensor.type_name == 'discrete':
            return self.saved_values.index(self.sensor.value.value)
        if self.sensor.type_name not in STRING_ADDRESS_TYPES:
            return self.sensor.value
        return self.saved_values.index(self.sensor.value)


class Watcher(aiokatcp.SensorWatcher):
    """Watcher class that connects to a katcp interface and updates the sensor values
       as they come in.

    Parameters
    ----------
    aiokatcp : aiokatcp.Client
        A instance of `aiokatcp.Client`

    logger : logging.Logger
        A configured logger
    """

    def __init__(self, client: aiokatcp.Client, logger: logging.Logger) -> None:
        super().__init__(client)
        self.sensor_metrics: dict = {}
        self.logger: logging.Logger = logger
        self.sync_state = aiokatcp.client.SyncState.DISCONNECTED

    async def wait_for_sensors(self) -> None:
        """Gives the `ioloop` some time to wait for the sensors as they are syncing

        Returns
        -------
        None
        """
        while len(self.sensors) == 0:
            await asyncio.sleep(1)

    def sensor_added(self, name: str, description: str, units: str, type_name: str,
                     *args: bytes) -> None:
        """Overrides `aiokatcp.SensorWatcher.sensor_added` Stores a `SensorMetric`
           object to be displayed.

        Returns
        -------
        None
        """
        super().sensor_added(name, description, units, type_name, *args)
        if type_name not in STRING_ADDRESS_TYPES:
            self.sensor_metrics[name] = SensorMetric(self.sensors[name])
        elif WORKAROUND_STRING_ADDRESS:
            self.sensor_metrics[name] = SensorMetric(self.sensors[name])
        self.logger.info(f"Added sensor {name}")

    def sensor_removed(self, name: str) -> None:
        """Overrides `aiokatcp.SensorWatcher.sensor_removed` Removes a stored
           `SensorMetric` object to be displayed.

        Returns
        -------
        None
        """
        if name in self.sensor_metrics:
            del(self.sensor_metrics[name])
        super().sensor_removed(name)
        self.logger.info(f"Removed sensor {name}")

    def sensor_updated(self, name: str, value: bytes,
                       status: aiokatcp.sensor.Sensor.Status,
                       timestamp: float) -> None:
        """Overrides `aiokatcp.SensorWatcher.sensor_updated` Updates a stored
           `SensorMetric` object to be displayed.

        Returns
        -------
        None
        """
        super().sensor_updated(name, value, status, timestamp)
        if name in self.sensor_metrics:
            self.sensor_metrics[name].update_sensor()

    def state_updated(self, state: aiokatcp.client.SyncState) -> None:
        """Overrides `aiokatcp.SensorWatcher.state_updated` Stores the connection state.

        Returns
        -------
        None
        """
        logger.info(f"SyncSate {state}")
        super().state_updated(state)
        self.sync_state = state


class SensorMetricCollector(object):
    """A metric collector for `prometheus_client`

    Decides what to display at the /metrics endpoint
    """

    def __init__(self, watcher: Watcher) -> None:
        """
        """
        self.watcher = watcher
        self.sync_states_list = list(aiokatcp.client.SyncState)

    def collect(self) -> GaugeMetricFamily:
        yield GaugeMetricFamily('katcp_sync_state',
                                f'KATCP sync state {self.sync_states_list}',
                                value=self.watcher.sync_state.value)
        if self.watcher.sync_state == aiokatcp.client.SyncState.SYNCED:
            for metric in self.watcher.sensor_metrics.values():
                description = metric.sensor.description
                if metric.sensor.type_name == 'discrete':
                    description = f"{description}, Enum Values: {metric.saved_values}"
                yield GaugeMetricFamily(metric.metric_name, description,
                                        value=metric.metric_value)


async def watch(args: argparse.Namespace, logger: logging.Logger) -> None:
    try:
        client = aiokatcp.Client(args.katcp_host, args.katcp_port)
        watcher = Watcher(client, logger)
        client.add_sensor_watcher(watcher)
        collector = SensorMetricCollector(watcher)
        REGISTRY.register(collector)
        async with client:
            await watcher.wait_for_sensors()
            while True:
                await asyncio.sleep(1)
    except Exception:
        logger.exception("Fatal error in watch task")
        raise


async def web_server(args: argparse.Namespace, loop, logger: logging.Logger) -> None:
    try:
        app = web.Application(logger=logger)
        app.router.add_get("/metrics", aio.web.server_stats)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', args.metrics_port)
        await site.start()
    except Exception:
        logger.exception("Fatal error in web_server task")
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--katcp_host', default=os.environ.get("KATCP_HOST", None))
    parser.add_argument('--katcp_port', type=int, default=os.environ.get("KATCP_PORT",
                        None))
    parser.add_argument('--metrics_port',
                        type=int, default=os.environ.get("METRICS_PORT", 8080))
    parser.add_argument('--workaround_strings', action='store_true')

    args = parser.parse_args()
    WORKAROUND_STRING_ADDRESS = os.environ.get("WORKAROUND_STRINGS",  # type: ignore
                                               args.workaround_strings)

    assert args.katcp_host, "KATCP host is required"
    assert args.katcp_port, "KATCP port is required"

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info(f"katcp_host {args.katcp_host}")
    logger.info(f"katcp_port {args.katcp_port}")
    logger.info(f"metrics_port {args.metrics_port}")
    logger.info(f"workaround_strings {args.workaround_strings}")

    loop = asyncio.get_event_loop()

    watch_task = loop.create_task(watch(args, logger))
    web_task = loop.create_task(web_server(args, loop, logger))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

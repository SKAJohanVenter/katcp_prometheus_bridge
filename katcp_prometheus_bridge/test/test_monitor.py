import logging
import sys
import unittest
import ipaddress

import asynctest

from aiokatcp import Sensor
from katcp_prometheus_bridge.katcp_prometheus_bridge import bridge


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestWatchNumericalOnly(asynctest.TestCase):

    async def setUp(self) -> None:
        client = unittest.mock.MagicMock()
        client.loop = self.loop
        self.watcher = bridge.Watcher(client, logger)
        bridge.WORKAROUND_STRING_ADDRESS = False

    async def test_sensors(self) -> None:
        self.watcher.sensor_added('foo_int', 'A sensor', 'F', 'integer')
        self.assertEqual(len(self.watcher.sensors), 1)

        # INT
        self.watcher.sensor_updated('foo_int', b'2', Sensor.Status.WARN, 123456790.0)
        self.assertEqual(self.watcher.sensors['foo_int'].value, 2)
        self.assertTrue('foo_int' in self.watcher.sensor_metrics)
        self.assertEqual(self.watcher.sensor_metrics['foo_int'].metric_value, 2.0)
        # Check update of metric
        self.watcher.sensor_updated('foo_int', b'3', Sensor.Status.WARN, 123456790.0)
        self.assertEqual(self.watcher.sensors['foo_int'].value, 3)
        self.assertEqual(self.watcher.sensor_metrics['foo_int'].metric_value, 3.0)
        # Check removal
        self.watcher.sensor_removed('foo_int')
        self.assertTrue('foo_int' not in self.watcher.sensors)
        self.assertTrue('foo_int' not in self.watcher.sensor_metrics)

        # FLOAT
        self.watcher.sensor_added('foo_float', 'A sensor', 'F', 'float')
        self.watcher.sensor_updated('foo_float', b'2.0', Sensor.Status.WARN, 123456790.0)
        self.assertEqual(self.watcher.sensors['foo_float'].value, 2.0)
        self.assertTrue('foo_float' in self.watcher.sensor_metrics)

        # TIMESTAMP
        self.watcher.sensor_added('foo_time', 'A sensor', 'F', 'timestamp')
        self.watcher.sensor_updated('foo_time', b'1564985117.871126', Sensor.Status.WARN,
                                    123456790.0)
        self.assertEqual(self.watcher.sensors['foo_time'].value, 1564985117.871126)
        self.assertTrue('foo_time' in self.watcher.sensor_metrics)

        # BOOLEAN
        self.watcher.sensor_added('foo_bool', 'A sensor', 'F', 'boolean')
        self.watcher.sensor_updated('foo_bool', b'1', Sensor.Status.WARN, 123456790.0)
        self.assertEqual(self.watcher.sensors['foo_bool'].value, 1)
        self.assertTrue('foo_bool' in self.watcher.sensor_metrics)

        # DISCRETE
        self.watcher.sensor_added('foo_disc', 'A sensor', '', 'discrete', b'ok',
                                  b'degraded', b'fail')
        self.watcher.sensor_updated('foo_disc', b'fail', Sensor.Status.WARN,
                                    123456790.0)
        self.assertTrue('foo_disc' in self.watcher.sensor_metrics)
        self.assertEqual(self.watcher.sensors['foo_disc'].value.value, b'fail')
        self.assertEqual(self.watcher.sensor_metrics['foo_disc'].metric_value, 2.0)

        # Check indexing
        self.watcher.sensor_updated('foo_disc', b'ok', Sensor.Status.WARN,
                                    123456790.0)
        self.assertEqual(self.watcher.sensors['foo_disc'].value.value, b'ok')
        self.assertEqual(self.watcher.sensor_metrics['foo_disc'].metric_value, 0.0)
        self.watcher.sensor_updated('foo_disc', b'degraded', Sensor.Status.WARN,
                                    123456790.0)
        self.assertEqual(self.watcher.sensors['foo_disc'].value.value, b'degraded')
        self.assertEqual(self.watcher.sensor_metrics['foo_disc'].metric_value, 1.0)

        # ADDRESS
        self.watcher.sensor_added('foo_addr', 'A sensor', '', 'address')
        self.watcher.sensor_updated('foo_addr', b'1.2.3.4', Sensor.Status.WARN,
                                    123456790.0)
        self.assertTrue('foo_addr' not in self.watcher.sensor_metrics)

        self.watcher.sensor_added('foo_string', 'A sensor', '', 'string')
        self.watcher.sensor_updated('foo_string', b'a string', Sensor.Status.WARN,
                                    123456790.0)
        self.assertTrue('foo_string' not in self.watcher.sensor_metrics)


class TestStringWorkaround(asynctest.TestCase):

    async def setUp(self) -> None:
        client = unittest.mock.MagicMock()
        client.loop = self.loop
        self.watcher = bridge.Watcher(client, logger)
        bridge.WORKAROUND_STRING_ADDRESS = True

    async def test_sensors(self) -> None:

        self.watcher.sensor_added('foo_addr', 'A sensor', '', 'address')
        self.watcher.sensor_updated('foo_addr', b'1.2.3.4', Sensor.Status.WARN,
                                    123456790.0)
        self.assertTrue('foo_addr' in self.watcher.sensor_metrics)
        self.assertEqual(self.watcher.sensors['foo_addr'].value.host,
                         ipaddress.ip_address('1.2.3.4'))
        self.assertEqual(self.watcher.sensor_metrics['foo_addr'].metric_value, 0.0)

        self.watcher.sensor_removed('foo_addr')
        self.assertTrue('foo_addr' not in self.watcher.sensors)
        self.assertTrue('foo_addr' not in self.watcher.sensor_metrics)

        self.watcher.sensor_added('foo_string', 'A sensor', '', 'string')
        self.watcher.sensor_updated('foo_string', b'a string', Sensor.Status.WARN,
                                    123456790.0)
        self.assertTrue('foo_string' in self.watcher.sensor_metrics)

        # Check index
        self.watcher.sensor_updated('foo_string', b'a string 2', Sensor.Status.WARN,
                                    123456790.0)
        self.watcher.sensor_updated('foo_string', b'a string 3', Sensor.Status.WARN,
                                    123456790.0)
        self.watcher.sensor_updated('foo_string', b'a string 4', Sensor.Status.WARN,
                                    123456790.0)
        self.assertEqual(self.watcher.sensor_metrics['foo_string'].metric_value,
                         3.0)

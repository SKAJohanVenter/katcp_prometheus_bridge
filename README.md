# katcp_prometheus_bridge
Connects to a katcp interface and publishes sensor values as Prometheus Gauge metrics.

Python 3.7+ is required.

## Caveats

Prometheus flattens metrics into a untyped time series, but katcp has several data types.


katcp data types are handled as follows:
 - `string` and `address`
    - By default they are ignored.
    - There is a workaround for these. Sensor values are are added to a list as they are retrieved. An index into that list for the current setting is returned. A user _may_ be able to infer the meaning of the index.
    - Enable it by adding the commandline option `--workaround_strings` or an environment variable named `WORKAROUND_STRINGS`
    - Usage of this option is however discouraged.
 - `bool`
    - 0.0 is False
    - 1.0 is True
 - `discrete`
    - When the sensor is added we know what the possible values are. An index into that list for the current value is returned.
    - The options are displayed in the `HELP` string.
 - `float`
    - Returned as is.
 - `int`
    - Retuned as its float value.

## Run in docker
- Check out the repo (or just the Dockerfile)
- Build the container
  - `docker build -t katcp_prometheus_bridge .`
- Run the container
  - `docker run -e "KATCP_HOST=<KATCP_HOST>" -e "KATCP_PORT=<KATCP_PORT>" -p 8080:8080  katcp_prometheus_bridge`
- Browse to http://0.0.0.0:8080/metrics


## TODO
- Expand tests
- Make sure `interface changed` from katcp is handled correctly
- Exit the asyncio loop cleanly upon exit
- Maybe add a mechanism to list which sensors to watch.

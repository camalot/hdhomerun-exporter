# hdhomerun-exporter

A prometheus exporter for hdhomerun devices on your network.

# METRICS

- `hdhomerun_tuners_available_total`: Total available tuners
- `hdhomerun_channels_available_total`: Total number of channels
- `hdhomerun_tuners_in_use`: Number of tuners currently in use
- `hdhomerun_tuners_available`: Number of available tuners
- `hdhomerun_update_available`: Indicates if there is a system update

# CONFIGURATION

All configuration is defined in a yaml file. Default location of the file: `./config/.hdhomerun.yml`. The location of this file can be set via an environment variable `HDHR_CONFIG_FILE`.

```yaml
---
tuners: # A list of devices
- hostname: hdhomerun01.home.local # host name or ip address of your hdhomerun
  useTLS: false # determines if it should use HTTPS or HTTP
  validateTLS: false # determines if certificates should be validated (if useTLS = true)
- hostname: hdhomerun02.home.local
  useTLS: false
  validateTLS: false
metrics:
  port: 2001 # Port for the http server to host the metrics
  pollingInterval: 300 # frequency, in seconds, to poll the metrics from the devices
```

To configure prometheus you add the following to your configuration for `scrape_configs`:

```yaml
- job_name: "hdhomerun"
  scrape_interval: 60s
  metrics_path: /metrics # the url path to hit to scrape the metrics.
  scheme: http
  static_configs:
  - targets:
    - '192.168.1.123:2001' # ip or host and port where to scrape the metrics
```

# DOCKER

You can use the provided `docker-compose.yml` or run directly with docker

```shell
docker run --rm --it \
	-e HDHR_CONFIG_FILE=/config/.hdhomerun.yml
	-v /path/to/config:/config:ro
	ghcr.io/camalot/hdhomerun-exporter:latest
```
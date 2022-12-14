# hdhomerun-exporter

A prometheus exporter for hdhomerun devices on your network.

# METRICS

- `hdhomerun_tuners_available_total`: Total available tuners
- `hdhomerun_channels_available_total`: Total number of channels
- `hdhomerun_tuners_in_use`: Number of tuners currently in use
- `hdhomerun_tuners_available`: Number of available tuners
- `hdhomerun_update_available`: Indicates if there is a system update
- `hdhomerun_up`: Indicates if the service is able to be polled

## SAMPLE
```
# HELP hdhomerun_tuners_available_total Total available tuners
# TYPE hdhomerun_tuners_available_total gauge
hdhomerun_tuners_available_total{host="hdhomerun01.home.local"} 0.0
hdhomerun_tuners_available_total{host="hdhomerun02.home.local"} 4.0
# HELP hdhomerun_channels_available_total Total number of channels
# TYPE hdhomerun_channels_available_total gauge
hdhomerun_channels_available_total{host="hdhomerun01.home.local"} 0.0
hdhomerun_channels_available_total{host="hdhomerun02.home.local"} 102.0
# HELP hdhomerun_tuners_in_use Number of tuners currently in use
# TYPE hdhomerun_tuners_in_use gauge
hdhomerun_tuners_in_use{host="hdhomerun01.home.local"} 0.0
hdhomerun_tuners_in_use{host="hdhomerun02.home.local"} 0.0
# HELP hdhomerun_tuners_available Number of available tuners
# TYPE hdhomerun_tuners_available gauge
hdhomerun_tuners_available{host="hdhomerun01.home.local"} 0.0
hdhomerun_tuners_available{host="hdhomerun02.home.local"} 4.0
# HELP hdhomerun_update_available Indicates if there is a system update
# TYPE hdhomerun_update_available gauge
hdhomerun_update_available{host="hdhomerun01.home.local"} 0.0
hdhomerun_update_available{host="hdhomerun02.home.local"} 0.0
# HELP hdhomerun_up Indicates if the service is able to be polled
# TYPE hdhomerun_up gauge
hdhomerun_up{host="hdhomerun01.home.local",service="fetch_update_status"} 0.0
hdhomerun_up{host="hdhomerun02.home.local",service="fetch_update_status"} 1.0
hdhomerun_up{host="hdhomerun01.home.local",service="fetch_available_channels"} 0.0
hdhomerun_up{host="hdhomerun02.home.local",service="fetch_available_channels"} 1.0
hdhomerun_up{host="hdhomerun01.home.local",service="fetch_tuners"} 0.0
hdhomerun_up{host="hdhomerun02.home.local",service="fetch_tuners"} 1.0
```
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
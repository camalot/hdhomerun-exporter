"""Application exporter"""

import os
import time
from prometheus_client import start_http_server, Gauge, Enum
import requests
import yaml
import codecs
import re
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
class AppConfig:
	def __init__(self, file):
		try:
			with codecs.open(file, encoding="utf-8-sig", mode="r") as f:
				settings = yaml.safe_load(f)
				self.__dict__.update(settings)
		except yaml.YAMLError as exc:
			print(exc)
		# self.metrics = MetricsConfig()

class TunerConfig:
	def __init__(self, hostname: str, useTls: bool, validateTls: bool):
		self.hostname = hostname
		self.useTls = useTls
		self.validateTls = validateTls

class MetricsConfig:
	def __init__(self, port: int, pollingInterval: int):
		self.port = port
		self.pollingInterval = pollingInterval

class HDHomeRuneMetrics:
	"""
	Representation of Prometheus metrics and loop to fetch and transform
	application metrics into Prometheus metrics.
	"""

	def __init__(self, config):
			self.namespace = "hdhomerun"
			self.polling_interval_seconds = config.metrics['pollingInterval']
			self.config = config
			self.tuners_available_total = Gauge(namespace=self.namespace, name=f"tuners_available_total", documentation="Total available tuners", labelnames=["host"])
			self.channels_available_total = Gauge(namespace=self.namespace, name=f"channels_available_total", documentation="Total number of channels", labelnames=["host"])
			self.tuners_in_use = Gauge(namespace=self.namespace, name=f"tuners_in_use", documentation="Number of tuners currently in use", labelnames=["host"])
			self.tuners_available = Gauge(namespace=self.namespace, name=f"tuners_available", documentation="Number of available tuners", labelnames=["host"])
			self.update_available = Gauge(namespace=self.namespace, name=f"update_available", documentation="Indicates if there is a system update", labelnames=["host"])

	def run_metrics_loop(self):
		"""Metrics fetching loop"""

		while True:
			print(f"begin metrics fetch")
			self.fetch()
			time.sleep(self.polling_interval_seconds)

	def fetch_tuners(self):
		for t in self.config.tuners:
			try:

				tuner = TunerConfig(t['hostname'], t['useTLS'], t['validateTLS'])
				resp = requests.get(url=self.build_url(tuner, "tuners.html"), timeout=5)
				data = resp.text
				regex = r"<tr>\s*<td>(?P<tuner>[^<]+)</td>\s*<td>(?P<state>[^<]+)</td></tr>"
				inUse = 0
				totalTuners = 0

				matches = re.finditer(regex, data, re.MULTILINE)
				for matchNum, match in enumerate(matches, start=1):
					totalTuners += 1
					if match.group(2) != "not in use" and match.group(2) != "none":
							inUse += 1
				self.tuners_available_total.labels(tuner.hostname).set(totalTuners)
				self.tuners_in_use.labels(tuner.hostname).set(inUse)
				self.tuners_available.labels(tuner.hostname).set(totalTuners - inUse)
			except Exception as e:
				print(e)
	def fetch_update_status(self):
		for t in self.config.tuners:
			try:
				tuner = TunerConfig(t['hostname'], t['useTLS'], t['validateTLS'])
				resp = requests.get(url=self.build_url(tuner, "upgrade_status.json"), timeout=5)
				data = resp.json()
				if "UpgradeAvailable" in data:
					self.update_available.labels(tuner.hostname).set(data["UpgradeAvailable"])
				else:
					self.update_available.labels(tuner.hostname).set(0)
			except Exception as e:
				print(e)
	def fetch_available_channels(self):
		for t in self.config.tuners:
			try:
				tuner = TunerConfig(t['hostname'], t['useTLS'], t['validateTLS'])
				resp = requests.get(url=self.build_url(tuner, "lineup.json?show=found"), timeout=5)
				data = resp.json()
				self.channels_available_total.labels(tuner.hostname).set(len(data))
			except Exception as e:
				print(e)

	def fetch(self):
		"""
		Get metrics from application and refresh Prometheus metrics with
		new values.
		"""
		self.fetch_update_status()
		self.fetch_available_channels()
		self.fetch_tuners()

	def build_url(self, tuner: TunerConfig, path: str):
		scheme = "http"
		if tuner.useTls:
			scheme = "https"
		return f"{scheme}://{tuner.hostname}/{path}"

def dict_get(dictionary, key, default_value = None):
    if key in dictionary.keys():
        return dictionary[key] or default_value
    else:
        return default_value

def main():
	"""Main entry point"""
	config_file = dict_get(os.environ, "HDHR_CONFIG_FILE", default_value="./config/.hdhomerun.yml")
	print(f"Using config file {config_file}")
	settings = AppConfig(config_file)

	print(f"start listening on :{settings.metrics['port']}")
	app_metrics = HDHomeRuneMetrics(settings)
	start_http_server(settings.metrics['port'])
	app_metrics.run_metrics_loop()


if __name__ == "__main__":
    main()

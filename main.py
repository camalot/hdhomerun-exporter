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

class DeviceSystemInfo:
	def __init__(self, model: str, firmware: str, device_id: str, mac_address: str, ip_address: str, subnet_mask: str):
		self.model = model
		self.firmware = firmware
		self.device_id = device_id
		self.mac_address = mac_address
		self.ip_address = ip_address
		self.subnet_mask = subnet_mask


class HDHomeRunMetrics:
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
			self.up = Gauge(namespace=self.namespace, name="up", documentation="Indicates if the service is able to be polled", labelnames=["host", "service"])
	def run_metrics_loop(self):
		"""Metrics fetching loop"""

		while True:
			print(f"begin metrics fetch")
			self.fetch()
			time.sleep(self.polling_interval_seconds)

	def fetch_tuners(self):
		for t in self.config.tuners:
			tuner = TunerConfig(t['hostname'], t['useTLS'], t['validateTLS'])
			try:
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
				self.tuners_available_total.labels(host=tuner.hostname).set(totalTuners)
				self.tuners_in_use.labels(host=tuner.hostname).set(inUse)
				self.tuners_available.labels(host=tuner.hostname).set(totalTuners - inUse)
				self.up.labels(host=tuner.hostname, service="fetch_tuners").set(1)
			except Exception as e:
				self.tuners_available_total.labels(host=tuner.hostname).set(0)
				self.tuners_in_use.labels(host=tuner.hostname).set(0)
				self.tuners_available.labels(host=tuner.hostname).set(0)

				self.up.labels(host=tuner.hostname, service="fetch_tuners").set(0)
				print(e)
	def fetch_update_status(self):
		for t in self.config.tuners:
			tuner = TunerConfig(t['hostname'], t['useTLS'], t['validateTLS'])
			try:
				resp = requests.get(url=self.build_url(tuner, "upgrade_status.json"), timeout=5)
				data = resp.json()
				if "UpgradeAvailable" in data:
					self.update_available.labels(tuner.hostname).set(data["UpgradeAvailable"])
				else:
					self.update_available.labels(tuner.hostname).set(0)
				self.up.labels(host=tuner.hostname, service="fetch_update_status").set(1)
			except Exception as e:
				self.update_available.labels(tuner.hostname).set(0)
				self.up.labels(host=tuner.hostname, service="fetch_update_status").set(0)
				print(e)
	def fetch_available_channels(self):
		for t in self.config.tuners:
			tuner = TunerConfig(t['hostname'], t['useTLS'], t['validateTLS'])
			try:
				resp = requests.get(url=self.build_url(tuner, "lineup.json?show=found"), timeout=5)
				data = resp.json()
				self.channels_available_total.labels(tuner.hostname).set(len(data))
				self.up.labels(host=tuner.hostname, service="fetch_available_channels").set(1)
			except Exception as e:
				self.channels_available_total.labels(tuner.hostname).set(0)
				self.up.labels(host=tuner.hostname, service="fetch_available_channels").set(0)
				print(e)

	def fetch_system_info(self):
		for t in self.config.tuners:
			tuner = TunerConfig(t['hostname'], t['useTLS'], t['validateTLS'])
			try:
				resp = requests.get(url=self.build_url(tuner, "tuners.html"), timeout=5)
				data = resp.text
				regex = r"<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td></tr>"

				matches = re.finditer(regex, data, re.MULTILINE)
				for matchNum, match in enumerate(matches, start=1):

					attr:str = match.group(1)
					val:str = match.group(2)
					model:str = ""
					firmware:str = ""
					deviceId:str = ""
					macAddr:str = ""
					ipAddr:str = ""
					subnetMask:str = ""
					if attr == "Hardware Model":
						model = val
					elif attr == "Firmware Version":
						firmware = val
					elif attr == "Device ID":
						deviceId = val
					elif attr == "MAC Address":
						macAddr = val
					elif attr == "IP Address":
						ipAddr = val
					elif attr == "Subnet Mask":
						subnetMask = val

					sysInfo = DeviceSystemInfo(model=model, firmware=firmware, device_id=deviceId, mac_address=macAddr, ip_address=ipAddr, subnet_mask=subnetMask)
					
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
	app_metrics = HDHomeRunMetrics(settings)
	start_http_server(settings.metrics['port'])
	app_metrics.run_metrics_loop()


if __name__ == "__main__":
    main()

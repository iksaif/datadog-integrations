import os
import re

import netatmo

from datadog_checks.base import AgentCheck

__version__ = "1.0.0"


def camel_to_snake(name):
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def metric_from_name(name):
    return camel_to_snake(name.replace(":", ".")).replace("._", ".")


class NetatmoCheck(AgentCheck):
    """ """

    PREFIX = "cozytouch."

    def __init__(self, *args, **kwargs):
        super(NetatmoCheck, self).__init__(*args, **kwargs)

    def check(self, instance):
        ws = netatmo.WeatherStation(self.instance)
        ws.get_data()
        tags = []
        for device in ws.devices:
            self.check_device(device, tags)

    def add_tags(self, device, tags, keys):
        tags = list(tags)
        for t in keys:
            if t in device:
                tags.append(t + ":" + str(device[t]))
        return tags

    def check_device(self, device, tags):
        tags = list(tags)
        tags = self.add_tags(device, tags, ["station_name", "home_id", "home_name"])

        for module in device.get("modules", []):
            self.check_device(module, tags)

        tags = self.add_tags(device, tags, ["firmware"])
        tags.extend(["device_type:" + device["type"]])

        for name, value in device["dashboard_data"].items():
            self.metric_for_data(name, value, tags)
        for k in [
            "last_setup",
            "battery_percent",
            "last_message",
            "last_seen",
            "rf_status",
            "battery_vp",
            "wifi_status",
            "last_status_store",
        ]:
            if k in device:
                self.metric_for_data(k, device[k], tags)

    def metric_for_data(self, name, value, tags):
        metric = metric_from_name(name)
        if type(value) in (int, float):
            self.gauge(self.PREFIX + metric, value, tags=tags)
        elif type(value) is str:
            t = tags + ["value:" + value]
            self.gauge(self.PREFIX + metric + ".by_value", 1, tags=t)
        else:
            print("unknown type %s (%s) for metric %s" % (type(value), value, metric))
            pass


if __name__ == "__main__":
    instance = {
      "client_id": os.getenv("CLIENT_ID"),
      "client_secret": os.getenv("CLIENT_SECRET"),
      "username": os.getenv("USERNAME"),
      "password": os.getenv("PASSWORD"),
      "device": os.getenv("DEVICE")
    }
    check = NetatmoCheck()
    check.check(instance)

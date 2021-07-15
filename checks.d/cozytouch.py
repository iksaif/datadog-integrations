import re
from datadog_checks.base import AgentCheck

from cozytouchpy import CozytouchClient
from cozytouchpy.exception import CozytouchException

__version__ = "1.0.0"


def camel_to_snake(name):
  name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
  return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def metric_from_name(name):
    return camel_to_snake(name.replace(':', '.')).replace('._', '.')


class CozyCouchCheck(AgentCheck):
    """
    """
    PREFIX = "cozytouch."


    def __init__(self, *args, **kwargs):
        super(CozyCouchCheck, self).__init__(*args, **kwargs)


    def device_info(self, device):
        #self.gauge(prefix + f.lower(), data[f], tags=tags)
        #self.monotonic_count(prefix + "energy", inverter["ETotal"], tags=tags)
        #print(repr(device))
        #print(dir(device))
        tags = [
            "name:" + device.name,
            "id:" + device.id,
            "place:" + device.place.name
        ]
        if hasattr(device, "operating_mode"):
            tags.append("operating_mode:" + device.operating_mode)
        
        for state in device.supported_states:
            value = device.get_state(state)
            metric = metric_from_name(state)
            if type(value) in (int, float):
                self.gauge(self.PREFIX + metric, value, tags=tags)
            else:
                pass
                #print("unknown type %s (%s) for metric %s" % (type(value), value, metric))

        if hasattr(device, "sensors") and len(device.sensors) > 0:
            print("\t\t Sensors")
            for sensor in device.sensors:
                sensor_tags = [
                    "sensor_id:" + sensor.id,
                    "sensor_name:" + sensor.name,
                    "sensor_widget:" + sensor.widget
                ] + tags
                for sensor_state in sensor.states:
                    name = sensor_state["name"]
                    value = sensor_state["value"]
                    metric = metric_from_name(name)
                    if type(value) in (int, float):
                        self.gauge(self.PREFIX + metric, value, tags=sensor_tags)
                    else:
                        pass
                        #print("unknown type %s (%s) for metric %s" % (type(value), value, metric))

    def gateway_info(self, gateway):
        tags = [
            "id:" + gateway.id,
            "version:" + gateway.version,
            "status:" + str(gateway.status),
        ]
        print(gateway.is_on)
        self.gauge(self.PREFIX + "gateway.is_on", int(gateway.is_on), tags=tags)
        
    async def check_async(self, instance):
        client = CozytouchClient(instance['username'], instance['password'])
        await client.connect()
        setup = await client.get_setup()

        for boiler in setup.boilers:
            self.device_info(boiler)

        for water_heater in setup.water_heaters:
            self.device_info(water_heater)

        for heater in setup.heaters:
            self.device_info(heater)

        for pod in setup.pods:
            self.device_info(pod)

        for gw in setup.gateways:
            self.gateway_info(gw)

    def check(self, instance):
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.check_async(instance))
        loop.close()

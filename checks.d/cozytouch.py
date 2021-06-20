import re
from datadog_checks.base import AgentCheck

from cozytouchpy import CozytouchClient
from cozytouchpy.exception import CozytouchException

__version__ = "1.0.0"


def camel_to_snake(name):
  name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
  return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


class CozyCouchCheck(AgentCheck):
    """
    """


    def __init__(self, *args, **kwargs):
        super(CozyCouchCheck, self).__init__(*args, **kwargs)


    def device_info(device):
        #self.gauge(prefix + f.lower(), data[f], tags=tags)
        #self.monotonic_count(prefix + "energy", inverter["ETotal"], tags=tags)
        tags = [
            "name:" + device.name,
            "build:" + device.build,
            "id:" + device.id,
            "place:" + device.place.name
        ]
        
        for state in device.supported_states:
            value = device.get_state(state)
            if type(value) in (int, float):
                snake_state = camel_to_snake(state.replace(':', '.'))
                self.gauge(self.prefix + snake_state, value, tags=tags)
                
        # device.is_on
        if hasattr(device, "operating_mode"):
            logger.info("\t\t Operating mode:{}".format(device.operating_mode))
        if hasattr(device, "sensors") and len(device.sensors) > 0:
            logger.info("\t\t Sensors")
            for sensor in device.sensors:
                logger.info("\t\t\t Id:{}".format(sensor.id))
                logger.info("\t\t\t Name:{}".format(sensor.name))
                logger.info("\t\t\t Type: {}".format(sensor.widget))
                for sensor_state in sensor.states:
                    logger.info(
                        "\t\t\t\t {name}: {value}".format(
                            name=sensor_state["name"], value=sensor_state["value"]
                        )
                    )


    def gateway_info(self, gateway):
        tags = [
            "id:" + gw.id,
            "version:" + gw.version,
            "status:" + gw.status,
        ]
        print(gw.is_on)
        self.gauge(self.prefix + "gateway.is_on", int(gw.is_on), tags=tags)
        
    def check(self, instance):
        client = CozytouchClient(isntance['username'], instance['password'])
        client.connect()
        client.get_setup()

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

        client.close()



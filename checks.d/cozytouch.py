import re
import os
import logging
import aiohttp
import asyncio

from cozytouchpy import CozytouchClient
from cozytouchpy.constant import USER_AGENT
from cozytouchpy.exception import (
    AuthentificationFailed,
    CozytouchException,
    HttpRequestFailed,
    HttpTimeoutExpired,
)

from datadog_checks.base import AgentCheck

__version__ = "1.0.0"


def camel_to_snake(name):
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def metric_from_name(name):
    return camel_to_snake(name.replace(":", ".")).replace("._", ".")


# From https://github.com/dubocr/overkiz-client/blob/master/src/Client.ts#L18
class AtlanticCozytouchClient(CozytouchClient):
    ATLANTIC_BASE_URL = "https://api.groupe-atlantic.com"
    ATLANTIC_TOKEN_URL = "{base_url}/token".format(base_url=ATLANTIC_BASE_URL)
    ATLANTIC_JWT_URL = "{base_url}/gacoma/gacomawcfservice/accounts/jwt".format(
        base_url=ATLANTIC_BASE_URL
    )
    ATLANTIC_BASIC_AUTH = (
        "czduc0RZZXdWbjVGbVV4UmlYN1pVSUM3ZFI4YTphSDEzOXZmbzA1ZGdqeDJkSFVSQkFTbmhCRW9h"
    )

    def __init__(self, username, password, *args, **kwargs):
        super().__init__(username, password, *args, **kwargs)

    async def connect(self):
        """Authenticate using username and userPassword."""

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic {token}".format(token=self.ATLANTIC_BASIC_AUTH),
        }
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }

        response_json, response = await self.___make_request(
            self.ATLANTIC_TOKEN_URL, method="POST", data=data, headers=headers
        )
        if response.status != 200:
            raise AuthentificationFailed(response.status)
        atlantic_token = response_json["access_token"]

        headers = {"Authorization": "Bearer " + atlantic_token + ""}

        response_json, response = await self.___make_request(
            self.ATLANTIC_JWT_URL, method="GET", headers=headers
        )
        if response.status != 200:
            raise AuthentificationFailed(response.status)
        jwt = response_json.replace('"', "")
        data = {"jwt": jwt}

        _, response = await self._CozytouchClient__make_request(
            "login",
            method="POST",
            data=data,
            json_encode=False,
        )

        if response.status != 200:
            raise AuthentificationFailed(response.status)
        self.is_connected = True
        self.cookies = {"JSESSIONID": response.cookies.get("JSESSIONID")}

    async def ___make_request(self, url, method="GET", data=None, headers=None):
        if data is None:
            data = {}

        if headers is None:
            headers = {}

        headers["User-Agent"] = USER_AGENT

        logging.debug("Request %s : %s", method, url)
        async with aiohttp.ClientSession(
            cookies=self.cookies, timeout=self.timeout
        ) as session:
            if method == "GET":
                try:
                    async with session.get(url, headers=headers) as resp:
                        response_json = await resp.json()
                        response = resp
                except aiohttp.ClientError as error:
                    raise HttpRequestFailed("Error Request") from error
                except asyncio.TimeoutError as error:
                    raise HttpTimeoutExpired("Error Request") from error
            else:
                try:
                    logging.debug("Json: %s", data)
                    async with session.post(url, headers=headers, data=data) as resp:
                        response_json = await resp.json()
                        response = resp
                except aiohttp.ClientError as error:
                    raise HttpRequestFailed("Error Request") from error
                except asyncio.TimeoutError as error:
                    raise HttpTimeoutExpired("Error Request") from error

        logging.debug("Response status : %s", response.status)
        logging.debug("Response json : %s", response_json)

        return response_json, response


class CozyCouchCheck(AgentCheck):
    """ """

    PREFIX = "cozytouch."

    def __init__(self, *args, **kwargs):
        super(CozyCouchCheck, self).__init__(*args, **kwargs)

    def device_info(self, device):
        tags = ["name:" + device.name, "id:" + device.id, "place:" + device.place.name]
        if hasattr(device, "operating_mode"):
            tags.append("operating_mode:" + device.operating_mode)

        for state in device.states:
            self.metric_for_state(state, tags)

        if hasattr(device, "sensors") and len(device.sensors) > 0:
            print("\t\t Sensors")
            for sensor in device.sensors.values():
                # move to sensor function
                sensor_tags = [
                    "sensor_id:" + sensor.id,
                    "sensor_name:" + sensor.name,
                    "sensor_widget:" + sensor.widget,
                ] + tags
                for sensor_state in sensor.states:
                    self.metric_for_state(state, sensor_tags)

    def metric_for_state(self, state, tags):
        name = state["name"]
        value = state["value"]
        metric = metric_from_name(name)
        if type(value) in (int, float):
            self.gauge(self.PREFIX + metric, value, tags=tags)
        elif type(value) is str:
            t = tags + ["value:" + value]
            self.gauge(self.PREFIX + metric + ".by_value", 1, tags=t)
        else:
            # print("unknown type %s (%s) for metric %s" % (type(value), value, metric))
            pass

    def place_info(self, place):
        # not sure what we could get where
        pass

    def sensor_info(self, sensor):
        # nothing done here because we do it in `device_info()`
        pass

    def gateway_info(self, gateway):
        tags = [
            "id:" + gateway.id,
            "version:" + gateway.version,
            "status:" + str(gateway.status),
        ]
        self.gauge(self.PREFIX + "gateway.is_on", int(gateway.is_on), tags=tags)

    async def check_async(self, instance):
        client = AtlanticCozytouchClient(instance["username"], instance["password"])
        await client.connect()
        setup = await client.get_setup()

        for place in setup.places.values():
            self.place_info(place)

        for device in setup.devices.values():
            self.device_info(device)

        for sensor in setup.sensors.values():
            self.sensor_info(sensor)

        for gw in setup.gateways.values():
            self.gateway_info(gw)

    def check(self, instance):
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except:
            loop = asyncio.new_event_loop()
        loop.run_until_complete(self.check_async(instance))
        loop.close()


if __name__ == "__main__":
    instance = {
        "username": os.getenv("USERNAME"),
        "password": os.getenv("PASSWORD"),
    }
    check = CozyCouchCheck()
    check.check(instance)

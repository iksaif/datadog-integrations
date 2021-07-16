# datadog-integrations

My own custom integrations for datadog

## Install

copy the content of `checks.d` and `conf.d` in `/etc/datadog/`

`sudo -u dd-agent -- /opt/datadog-agent/embedded/bin/python3 -m pip install -r requirements.txt`

## sbfspot

An integration for https://github.com/SBFspot/SBFspot/wiki, an open source project to get actual and archive data out of an SMA® inverter over Bluetooth or Ethernet.

## cozytouch

An integration for cozytouh using cozytouchpy.
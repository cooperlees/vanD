# vanD

_All your recreational van data collecting could ever need!_

vanD is a Ubuntu running Raspberry Pi telemetry collection daemon. It's been design to support various
components/modules and was written for @cooperlees's [2021 Winnebago Revel](https://vanlife.cooperlees.com/).
My main goal is to collect timeseries data (via [Prometheus](https://prometheus.io/docs/introduction/overview/))
from a cloud VPS for monitoring and baseline components when the RV has LTE/5G/Wifi available.

## Supported Components / Modules

- Lithionics (Li3) Batteries
  - Read the Bluetooth LE serial data and convert to Prometheus gauges

# Install

From GitHub:

- `pip install git+https://github.com/cooperlees/vanD`
- `sudo cp vand.json /etc/`

Optional - Run via [systemd](https://www.freedesktop.org/wiki/Software/systemd/):

- `sudo cp vanD.service /etc/systemd/system`
- `sudo systemctl daemon-reload`
- `sudo systemctl enable vanD`
- `sudo systemctl start vanD`

# Running

**vanD** is a daemon that binds to two ports

- `prometheus_exporter_port`: TCP port number for prometheus exporter
  - Default: 31337
- `web_port`: On Box Dashboard Port
  - Default: 8080

To start vanD all you need to do is pass a config file:

- `vanD [--debug] /path/to/vand.json`

# Configuration

vanD is all JSON configuration file driven. There is a main `vanD` section for generic options
and then will have a section per plugin to enable and set settings.

## vanD Options

- `prometheus_exporter_port`: TCP Port for the [Prometheus Exporter](https://pypi.org/project/aioprometheus/)
- `scan_time`: How long to scan for BLE DEvices
- `statistics_refresh_interval`: How often to update Prometheus Metrics from each plugin
- `web_port`: TCP Port for the local Web Dashboard

# Grafana Dashboards

- [Li3 Dashboard](https://grafana.com/grafana/dashboards/15649)
  - Dashboard showing all the stats collected by vanD for Li3 Batteries

# Development

The code is all >= **Python 3.9 asyncio** code.

```console
python3 -m venv [--upgrade-deps] /tmp/tv
/tmp/tv/bin/pip install -e .
```

## Run Tests

For testing we use [ptr](https://github.com/facebookincubator/ptr/).

```console
/tmp/tv/bin/ptr [-k] [--print-cov] [--debug] [--venv]
```

- `-k`: keep testing venv ptr creates
- `--print-cov`: handy to see what coverage is on all files
- `--debug`: Handy to see all commands run so you can run a step manually
- `--venv`: Reuse an already created venv (much faster to launch + run all CI)

### Manual formatting

- We try to `prettier` format _.md_ files.
  - `prettier -w *.md`

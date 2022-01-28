# vanD

*All your recreational van data collecting could ever need!*

vanD is my attempt of making a Raspberry Pi collect telemetry from various
components of my [2021 Winnebago Revel](https://vanlife.cooperlees.com/).
My main goal is to timeseries data for interest and monitoring while she
is parked with LTE/5G/Wifi available.

## Supported Components / Modules

- Li3 Batteries
  - Read the Bluetooth LE serial data and expose via pro

# Install

From GitHub:
- `pip install git+https://github.com/cooperlees/vanD`

# Development

The code is all >= Python 3.9 asyncio code.

```console
python3 -m venv [--upgrade-deps] /tmp/tv
/tmp/tv/bin/pip install -e .
````

## Run Tests

For testing we use [ptr](https://github.com/facebookincubator/ptr/).

```console
/tmp/tv/bin/ptr [-k] [--print-cov] [--debug] [--venv]
```

- `-k`: keep testing venv ptr creates
- `--print-cov`: handy to see what coverage is on all files
- `--debug`: Handy to see all commands run so you can run a step manually
- `--venv`: Reuse an already created venv (much faster to launch + run all CI)

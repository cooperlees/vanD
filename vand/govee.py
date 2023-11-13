import asyncio
import logging
from dataclasses import dataclass
from time import time
from typing import Any, Awaitable, Dict, Optional, Sequence

from aioprometheus import Gauge
from aioprometheus.collectors import Registry
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError


FORMAT_PRECISION = ".2f"
GOVEE_BT_MAC_OUI_PREFIX = "A4:C1:38"
LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherMetrics:
    battery_pct_left: float
    humidity: float
    rssi: int
    temperature_c: float
    temperature_f: float


class HS075S:
    # H5075_UPDATE_UUID16 = UUID16(0xEC88)

    def __init__(
        self,
        dev_name: str,
        mac_address: str,
        service_uuid: str,
        characteristic: str,
        timeout: float,
    ) -> None:
        self.bleak_device: Optional[BLEDevice] = None
        self.dev_name = dev_name
        self.mac_address = mac_address
        self.float = timeout
        self.service_uuid = service_uuid
        self.characteristic = characteristic
        self.timeout = timeout
        self.stats: Dict[str, WeatherMetrics] = {}

    def decode_temp_in_c(self, encoded_data: int) -> str:
        """Decode H5075 Temperature into degrees Celcius"""
        return format((encoded_data / 10000), FORMAT_PRECISION)

    def decode_temp_in_f(self, encoded_data: int) -> str:
        """Decode H5075 Temperature into degrees Fahrenheit"""
        return format((((encoded_data / 10000) * 1.8) + 32), FORMAT_PRECISION)

    def decode_humidity(self, encoded_data: int) -> str:
        """Decode H5075 percent humidity"""
        return format(((encoded_data % 1000) / 10), FORMAT_PRECISION)

    def telemetry_handler(self, _sender: str, data: bytes) -> None:
        print(f"{self.dev_name}:\n{data!r}")  # COOPER

    async def listen(self) -> None:
        if not self.bleak_device:
            raise BleakError(f"{self.dev_name} was not found in bleak scan!")

        LOG.info(f"Attempting to start a notify for {self.dev_name}")
        started_notify_uuid = ""
        async with BleakClient(self.bleak_device) as client:
            services = await client.get_services()
            for service in services:
                if service.uuid != self.service_uuid:
                    continue

                for characteristic in service.characteristics:
                    if characteristic.uuid == self.characteristic:
                        LOG.info(
                            f"Starting notify for {self.dev_name}:{self.service_uuid}:"
                            + f"{self.characteristic}"
                        )
                        await client.start_notify(
                            characteristic.uuid, self.telemetry_handler
                        )
                        started_notify_uuid = characteristic.uuid

            if not started_notify_uuid:
                LOG.error(
                    f"{self.dev_name} is not listening to '{started_notify_uuid}'!!"
                )
                return

            # Block while we read Bluetooth LE
            # TODO: Find if a better asyncio way to allow clean exit
            # Always cleanup the notify
            try:
                while True:
                    await asyncio.sleep(1)
            finally:
                LOG.info(f"Cleaning up bleak notify for {started_notify_uuid}")
                await client.stop_notify(started_notify_uuid)


class Hygrometers:
    def __init__(
        self, config: Dict, registry: Registry, stat_preifx: str = "govee_"
    ) -> None:
        self.config = config
        self.prom_registry = registry
        self.stat_preifx = stat_preifx
        self.hygrometers = []
        for id, h_settings in self.config.items():
            LOG.debug(f"Loading battery {id}: {h_settings}")
            self.hygrometers.append(HS075S(**h_settings))

        self.prom_stats = {
            # "battery_voltage": Gauge(
            #    f"{self.stat_preifx}battery_voltage",
            #    "Current volts of the battery",
            #    registry=self.prom_registry,
            # ),
            "temperature_f": Gauge(
                f"{self.stat_preifx}temperature_f",
                "Current temperature in Fahrenheit freedom units",
                registry=self.prom_registry,
            ),
        }

    async def scan_devices(self, scan_time: float) -> None:
        service_uuids = {h.service_uuid for h in self.hygrometers}
        LOG.info(f"Scanning for BLE Hygrometers with service_uuids {service_uuids}")
        scanner = BleakScanner(service_uuids=service_uuids)  # type: ignore
        discovered_devices = await scanner.discover(timeout=scan_time)
        found_devs = 0
        for dd in discovered_devices:
            for h in self.hygrometers:
                if dd.address == h.mac_address:
                    h.bleak_device = dd
                    found_devs += 1
                    continue
        LOG.info(
            f"Found {found_devs} BLE Hygrometers with service_uuids {service_uuids}"
        )

    async def stats_refresh(self, refresh_interval: float) -> None:
        while True:
            stat_collect_start_time = time()
            for hydrometer in self.hygrometers:
                if not hydrometer.stats:
                    LOG.error(
                        f"{hydrometer.dev_name} does not have valid stats ... skipping."
                    )
                    continue

                for stat_name, prom_metric in self.prom_stats.items():
                    prom_metric.set(
                        {
                            "dev_name": hydrometer.dev_name,
                            "mac_address": hydrometer.mac_address,
                            "characteristic": hydrometer.characteristic,
                            "service_uuid": hydrometer.service_uuid,
                        },
                        getattr(hydrometer.stats, stat_name),
                    )
                LOG.info(f"Updated {hydrometer.dev_name} stats")
            run_time = time() - stat_collect_start_time
            sleep_time = (
                refresh_interval - run_time if run_time < refresh_interval else 0
            )
            LOG.info(
                f"{HS075S.__name__} has refreshed prometheus stats in {run_time}s. "
                + f"Sleeping for {sleep_time}s"
            )
            await asyncio.sleep(sleep_time)

    async def get_awaitables(self, refresh_interval: float) -> Sequence[Awaitable[Any]]:
        coros = [self.stats_refresh(refresh_interval)]
        coros.extend([b.listen() for b in self.hygrometers])
        return coros

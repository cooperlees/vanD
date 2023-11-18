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


LOG = logging.getLogger(__name__)


# 1309,327,327,328,327,32,39,0,79,000000
@dataclass(frozen=True)
class Li3TelemetryStats:
    battery_voltage: float
    cell_1_voltage: float
    cell_2_voltage: float
    cell_3_voltage: float
    cell_4_voltage: float
    bms_temperature: float
    battery_temperature: float
    battery_power: float  # This will be amps or watts ...
    battery_soc: float
    fault_code: int  # This is hex converted to an int


class Li3Battery:
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

        self.str_data = ""
        self.stats: Optional[Li3TelemetryStats] = None

    def _telementary_handler(self, sender: str, data: bytes) -> None:
        self.raw_data = data
        tmp_str_data = data.decode("ascii")
        if tmp_str_data.startswith(","):
            self.str_data += tmp_str_data.strip()
            csv_data = self.str_data.split(",")
            self.stats = Li3TelemetryStats(
                float(csv_data[0]) / 100,
                float(csv_data[1]) / 100,
                float(csv_data[2]) / 100,
                float(csv_data[3]) / 100,
                float(csv_data[4]) / 100,
                float(csv_data[5]),
                float(csv_data[6]),
                float(csv_data[7]),
                float(csv_data[8]),
                int(csv_data[9], 16),
            )
        # no idea what &,1,114,006880 is.. throw it away for now
        elif "&" not in tmp_str_data:
            self.str_data = tmp_str_data

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
                            characteristic.uuid, self._telementary_handler
                        )
                        started_notify_uuid = characteristic.uuid

            if not started_notify_uuid:
                LOG.error(
                    f"{self.dev_name} is not listening to {started_notify_uuid}!!"
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


class RevelBatteries:
    def __init__(
        self, config: Dict, registry: Registry, stat_preifx: str = "li3_"
    ) -> None:
        self.config = config
        self.prom_registry = registry
        self.stat_preifx = stat_preifx
        self.batteries = []
        for id, battery_settings in self.config["li3"].items():
            LOG.debug(f"Loading battery {id}: {battery_settings}")
            self.batteries.append(Li3Battery(**battery_settings))

        self.prom_stats = {
            "battery_voltage": Gauge(
                f"{self.stat_preifx}battery_voltage",
                "Current volts of the battery",
                registry=self.prom_registry,
            ),
            "cell_1_voltage": Gauge(
                f"{self.stat_preifx}cell_1_voltage",
                "Battery Cell 1 Voltage",
                registry=self.prom_registry,
            ),
            "cell_2_voltage": Gauge(
                f"{self.stat_preifx}cell_2_voltage",
                "Battery Cell 2 Voltage",
                registry=self.prom_registry,
            ),
            "cell_3_voltage": Gauge(
                f"{self.stat_preifx}cell_3_voltage",
                "Battery Cell 3 Voltage",
                registry=self.prom_registry,
            ),
            "cell_4_voltage": Gauge(
                f"{self.stat_preifx}cell_4_voltage",
                "Battery Cell 4 Voltage",
                registry=self.prom_registry,
            ),
            "bms_temperature": Gauge(
                f"{self.stat_preifx}bms_temperature",
                "The temperature of the BMS",
                registry=self.prom_registry,
            ),
            "battery_temperature": Gauge(
                f"{self.stat_preifx}battery_temperature",
                "Battery temperature - Remember won't charge if to cold/hot",
                registry=self.prom_registry,
            ),
            "battery_power": Gauge(
                f"{self.stat_preifx}battery_power",
                "Battery current power charge or draw",
                registry=self.prom_registry,
            ),
            "battery_soc": Gauge(
                f"{self.stat_preifx}battery_soc",
                "Percentage of battery charge left",
                registry=self.prom_registry,
            ),
            "fault_code": Gauge(
                f"{self.stat_preifx}fault_code",
                "Type of Battery fault (Hex converted to int)",
                registry=self.prom_registry,
            ),
        }

    async def scan_devices(self, scan_time: float) -> None:
        service_uuids = {b.service_uuid for b in self.batteries}
        LOG.info(f"Scanning for BLE Batteries with service_uuids {service_uuids}")
        scanner = BleakScanner(service_uuids=list(service_uuids))
        discovered_devices = await scanner.discover(timeout=scan_time)
        found_devs = 0
        for dd in discovered_devices:
            for b in self.batteries:
                if dd.address == b.mac_address:
                    b.bleak_device = dd
                    found_devs += 1
                    continue
        LOG.info(f"Found {found_devs} BLE Batteries with service_uuids {service_uuids}")

    async def stats_refresh(self, refresh_interval: float) -> None:
        while True:
            stat_collect_start_time = time()
            for battery in self.batteries:
                if not battery.stats:
                    LOG.error(
                        f"{battery.dev_name} does not have valid stats ... skipping."
                    )
                    continue

                for stat_name, prom_metric in self.prom_stats.items():
                    prom_metric.set(
                        {
                            "dev_name": battery.dev_name,
                            "mac_address": battery.mac_address,
                            "characteristic": battery.characteristic,
                            "service_uuid": battery.service_uuid,
                        },
                        getattr(battery.stats, stat_name),
                    )
                LOG.info(f"Updated {battery.dev_name} stats")
            run_time = time() - stat_collect_start_time
            sleep_time = (
                refresh_interval - run_time if run_time < refresh_interval else 0
            )
            LOG.info(
                f"{RevelBatteries.__name__} has refreshed prometheus stats in {run_time}s. "
                + f"Sleeping for {sleep_time}s"
            )
            await asyncio.sleep(sleep_time)

    async def get_awaitables(self, refresh_interval: float) -> Sequence[Awaitable[Any]]:
        coros = [self.stats_refresh(refresh_interval)]
        coros.extend([b.listen() for b in self.batteries])
        return coros

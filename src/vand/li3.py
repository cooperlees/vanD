import asyncio
import logging
from dataclasses import dataclass
from time import time
from typing import Any, Awaitable, Dict, Optional, Sequence

from aioprometheus import Gauge
from aioprometheus.collectors import Registry
from bleak import BleakClient, BleakScanner  # type: ignore
from bleak.exc import BleakError  # type: ignore


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
        device = await BleakScanner.find_device_by_address(
            self.mac_address, timeout=self.timeout
        )
        if not device:
            raise BleakError(
                f"A device with address {self.mac_address} could not be found."
            )

        async with BleakClient(device) as client:
            services = await client.get_services()
            for service in services:
                if service.uuid != self.service_uuid:
                    continue

                for character in service.characteristics:
                    await client.start_notify(character.uuid, self._telementary_handler)

            # Block while we read Bluetooth LE
            # TODO: Find if a better asyncio way to allow clean exit
            while True:
                await asyncio.sleep(1)


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

    async def stats_refresh(self, refresh_interval) -> None:
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
            run_time = time() - stat_collect_start_time
            sleep_time = (
                refresh_interval - run_time if run_time < refresh_interval else 0
            )
            LOG.info(
                f"{RevelBatteries.__name__} has refreshed prometheus stats. Sleeping for {sleep_time}"
            )
            await asyncio.sleep(sleep_time)

    def get_awaitables(self, refresh_interval: float) -> Sequence[Awaitable[Any]]:
        coros = [self.stats_refresh(refresh_interval)]
        coros.extend([b.listen() for b in self.batteries])
        return coros

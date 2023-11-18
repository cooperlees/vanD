import asyncio
import logging
from dataclasses import dataclass
from time import sleep, time
from typing import Any, Awaitable, Dict, Sequence

import bleson
from aioprometheus import Gauge
from aioprometheus.collectors import Registry
from bleson import get_provider, Observer, UUID16


# Disable warnings from bleeson
bleson.logger.set_level(bleson.logger.ERROR)


LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherMetrics:
    battery_pct_left: float
    humidity: float
    rssi: int
    temperature_c: float
    temperature_f: float


class HS075S:
    FORMAT_PRECISION = ".2f"
    H5075_UPDATE_UUID16 = UUID16(0xEC88)

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
        self.stats = WeatherMetrics(
            battery_pct_left=0,
            humidity=0,
            rssi=0,
            temperature_c=0,
            temperature_f=0,
        )

        self.adapter = get_provider().get_adapter()
        self.observer = Observer(self.adapter)
        self.observer.on_advertising_data = self.process_data

    def __del__(self) -> None:
        self.observer.stop()

    def decode_temp_in_c(self, encoded_data: int) -> float:
        """Decode H5075 Temperature into degrees Celcius"""
        return float(format((encoded_data / 10000), self.FORMAT_PRECISION))

    def decode_temp_in_f(self, encoded_data: int) -> float:
        """Decode H5075 Temperature into degrees Fahrenheit"""
        return float(
            format((((encoded_data / 10000) * 1.8) + 32), self.FORMAT_PRECISION)
        )

    def decode_humidity(self, encoded_data: int) -> float:
        """Decode H5075 percent humidity"""
        return float(format(((encoded_data % 1000) / 10), self.FORMAT_PRECISION))

    # Ran in asyncio executor thread
    def listen(self) -> None:
        while True:
            self.observer.start()
            sleep(2)  # TODO: Maybe make configurable
            self.observer.stop()

    # TODO: workout the type
    def process_data(self, advertisement: Any) -> None:
        if advertisement.address.address != self.mac_address:
            LOG.debug(f"Ignoring advertisement from {advertisement.address.address}")
            return

        if self.H5075_UPDATE_UUID16 not in advertisement.uuid16s:
            LOG.debug(
                f"Ignoring advertisement from {self.mac_address} as we don't have the correct UUID"
            )
            return

        encoded_data = int(advertisement.mfg_data.hex()[6:12], 16)
        self.stats = WeatherMetrics(
            battery_pct_left=int(advertisement.mfg_data.hex()[12:14], 16),
            humidity=self.decode_humidity(encoded_data),
            rssi=advertisement.rssi if advertisement.rssi is not None else 0,
            temperature_c=self.decode_temp_in_c(encoded_data),
            temperature_f=self.decode_temp_in_f(encoded_data),
        )


class Hygrometers:
    def __init__(
        self, config: Dict, registry: Registry, stat_preifx: str = "govee_"
    ) -> None:
        self.config = config
        self.prom_registry = registry
        self.stat_preifx = stat_preifx
        self.hygrometers = []
        for id, h_settings in self.config.items():
            LOG.debug(f"Loading hygrometer {id}: {h_settings}")
            self.hygrometers.append(HS075S(**h_settings))

        self.prom_stats = {
            "battery_pct_left": Gauge(
                f"{self.stat_preifx}battery_pct_left",
                "Percentage of battery left",
                registry=self.prom_registry,
            ),
            "humidity": Gauge(
                f"{self.stat_preifx}humidity",
                "Humidity percentage",
                registry=self.prom_registry,
            ),
            "rssi": Gauge(
                f"{self.stat_preifx}rssi",
                "RSSI - Bluetooth signal strength I think?",
                registry=self.prom_registry,
            ),
            "temperature_c": Gauge(
                f"{self.stat_preifx}temperature_c",
                "Current temperature in sane Celsius",
                registry=self.prom_registry,
            ),
            "temperature_f": Gauge(
                f"{self.stat_preifx}temperature_f",
                "Current temperature in Fahrenheit freedom units",
                registry=self.prom_registry,
            ),
        }

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
        loop = asyncio.get_running_loop()
        coros = [self.stats_refresh(refresh_interval)]
        coros.extend([loop.run_in_executor(None, b.listen) for b in self.hygrometers])  # type: ignore
        return coros

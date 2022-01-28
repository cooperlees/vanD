import asyncio
import logging
from typing import Awaitable, Dict, List

from bleak import BleakClient, BleakScanner  # type: ignore
from bleak.exc import BleakError  # type: ignore


LOG = logging.getLogger(__name__)


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

    def _telementary_handler(self, sender: str, data: bytes) -> None:
        # Seems last event in series is a bit shorter
        # and no idea what &,1,114,006880 is.. throw it away for now
        if len(data) == 16:
            print(data)
            self.str_data = ""
            self.raw_data = b""
            return

        self.raw_data = data
        self.str_data = data.decode("ascii")
        print(self.str_data)

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
    def __init__(self, config: Dict) -> None:
        self.config = config
        self.batteries = []
        for id, battery_settings in self.config["li3"].items():
            LOG.debug(f"Loading battery {id}: {battery_settings}")
            self.batteries.append(Li3Battery(**battery_settings))

    def get_coros(self) -> List[Awaitable]:
        return [b.listen() for b in self.batteries]

#!/usr/bin/env python3

import asyncio
import json
import sys

from bleak import BleakClient, BleakScanner  # type: ignore


async def find_devs() -> None:
    with open(sys.argv[1], "r") as cfp:
        conf = json.load(cfp)
    for _ids, li3_dev in conf["li3"].items():
        mac = li3_dev["mac_address"]
        device = await BleakScanner.find_device_by_address(mac, timeout=5.0)

        print(li3_dev["dev_name"], mac)
        async with BleakClient(device) as client:
            services = await client.get_services()
            for service in services:
                print(service)
                for character in service.characteristics:
                    print(character)


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(find_devs())

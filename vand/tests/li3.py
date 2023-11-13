#!/usr/bin/env python3

import unittest

from aioprometheus.collectors import Registry

from vand import li3
from vand.tests.li3_fixtures import FAKE_LI3_BINARY_DATA, TEST_LI3_CONFIG


class TestLi3Battery(unittest.TestCase):
    def setUp(self) -> None:
        self.li3b = li3.Li3Battery(**TEST_LI3_CONFIG["li3"]["1"])

    def test_telemetry_hander(self) -> None:
        for data in FAKE_LI3_BINARY_DATA:
            self.li3b.telemetry_handler("unittest", data)
        # See we have the str data we expect
        self.assertEqual("1309,327,327,328,327,32,39,0,79,000000", self.li3b.str_data)
        # Ensure stats is not None
        self.assertIsNotNone(self.li3b.stats)
        # Ensure Telemetry Stats are what we expect
        expected_li3ts = li3.Li3TelemetryStats(
            battery_voltage=13.09,
            cell_1_voltage=3.27,
            cell_2_voltage=3.27,
            cell_3_voltage=3.28,
            cell_4_voltage=3.27,
            bms_temperature=32.0,
            battery_temperature=39.0,
            battery_power=0.0,
            battery_soc=79.0,
            fault_code=0,
        )
        self.assertEqual(expected_li3ts, self.li3b.stats)


class TestRevelBatteries(unittest.TestCase):
    def setUp(self) -> None:
        self.prom_registry = Registry()
        self.rb = li3.RevelBatteries(TEST_LI3_CONFIG, self.prom_registry)

    def test_init_worked(self) -> None:
        self.assertEqual(2, len(self.rb.batteries))

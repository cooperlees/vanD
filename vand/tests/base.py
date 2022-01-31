#!/usr/bin/env python3

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from click.testing import CliRunner

from vand.main import _load_config, main
from vand.tests.li3 import TestLi3Battery, TestRevelBatteries  # noqa: F401


class TestCLI(unittest.TestCase):
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0

    def test_load_config(self) -> None:
        with TemporaryDirectory() as td:
            tmp_config = Path(td) / "unittest.json"
            with tmp_config.open("w") as tcfp:
                json.dump({"JSON": "file"}, tcfp)
            loaded_json = _load_config(tmp_config)
            self.assertTrue("JSON" in loaded_json)

    def test_load_config_no_exist(self) -> None:
        self.assertFalse(_load_config(Path("/does/not/exist.json")))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

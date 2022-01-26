#!/usr/bin/env python3

import unittest

from click.testing import CliRunner

from vand.main import main


class TestCLI(unittest.TestCase):
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

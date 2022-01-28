#!/usr/bin/env python3

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Dict, List, Union

import click

from vand.li3 import RevelBatteries


LOG = logging.getLogger(__name__)


def _handle_debug(
    ctx: click.core.Context,
    param: Union[click.core.Option, click.core.Parameter],
    debug: Union[bool, int, str],
) -> Union[bool, int, str]:
    """Turn on debugging if asked otherwise INFO default"""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s: %(message)s (%(filename)s:%(lineno)d)",
        level=log_level,
    )
    return debug


def _load_config(conf_path: Path) -> Dict:
    if not conf_path.exists():
        LOG.error(f"{conf_path} does not exist. Exiting.")
        return {}
    with conf_path.open("rb") as cfp:
        return json.load(cfp)


def _start_modules(conf: Dict[str, Any]) -> List[Awaitable]:
    coros: List[Awaitable] = []
    if "li3" in conf.keys():
        coros.extend(RevelBatteries(conf).get_coros())
        LOG.debug("Added li3 coros ...")
    LOG.info(f"Loaded {len(coros)} modules ... Starting ...")
    return coros


async def async_main(
    debug: bool,
    config_path: str,
) -> int:
    conf = _load_config(Path(config_path))
    if not conf:
        return 1
    await asyncio.gather(*_start_modules(conf))
    return 0


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--debug",
    is_flag=True,
    callback=_handle_debug,
    show_default=True,
    help="Turn on debug logging",
)
@click.argument("config-path", nargs=1)
@click.pass_context
def main(
    ctx: click.Context,
    **kwargs,
) -> None:
    """vanD: All your RV monitoring needs"""
    ctx.exit(asyncio.run(async_main(**kwargs)))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Dict, List, Tuple, Union

import click
from aioprometheus.collectors import Registry
from aioprometheus.service import Service

from vand.li3 import RevelBatteries


LOG = logging.getLogger(__name__)


def _handle_debug(
    ctx: click.core.Context,
    param: Union[click.core.Option, click.core.Parameter],
    debug: Union[bool, int, str],
) -> Union[bool, int, str]:  # pragma: no cover
    """Turn on debugging if asked otherwise INFO default"""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s: %(message)s (%(filename)s:%(lineno)d)",
        level=log_level,
    )
    return debug


async def _blocking_coro() -> None:  # pragma: no cover
    """Hack for testing on a box with box bluetooth - e.g. cooper's mac"""
    while True:
        await asyncio.sleep(1)


def _load_config(conf_path: Path) -> Dict:
    if not conf_path.exists():
        LOG.error(f"{conf_path} does not exist. Exiting.")
        return {}
    with conf_path.open("rb") as cfp:
        return dict(json.load(cfp))


async def _load_modules(
    conf: Dict[str, Any]
) -> Tuple[List[Awaitable], List[Awaitable]]:
    cleanup_coros: List[Awaitable] = []
    main_coros: List[Awaitable] = []
    no_modules = True
    prom_registry = Registry()

    # Monitor Li3 Batteries if configured
    if "li3" in conf.keys():
        rb = RevelBatteries(conf, prom_registry)
        await rb.scan_devices(conf["vanD"]["scan_time"])
        main_coros.extend(
            await rb.get_awaitables(conf["vanD"]["statistics_refresh_interval"])
        )
        LOG.info("Loaded li3 awaitables ...")
        no_modules = False

    # Hack for developing locally to block exiting
    if no_modules:
        main_coros.append(_blocking_coro())

    # Start prometheus server
    prom_service = Service(registry=prom_registry)
    main_coros.append(prom_service.start(port=conf["vanD"]["prometheus_exporter_port"]))
    cleanup_coros.append(prom_service.stop())

    LOG.info(
        f"Loaded {len(main_coros)} awaitables to run and have "
        + f"{len(cleanup_coros)} coros ready for cleanup"
    )
    return main_coros, cleanup_coros


async def async_main(
    debug: bool,
    config_path: str,
) -> int:
    conf = _load_config(Path(config_path))
    if not conf:
        return 1
    main_coros, cleanup_coros = await _load_modules(conf)
    # TODO: Handle cleanup and exiting cleanly from signals - e.g. SIGTERM
    try:
        await asyncio.gather(*main_coros)
    finally:
        await asyncio.gather(*cleanup_coros)
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
    **kwargs: Any,
) -> None:
    """vanD: All your RV monitoring needs"""
    ctx.exit(asyncio.run(async_main(**kwargs)))


if __name__ == "__main__":  # pragma: no cover
    main()

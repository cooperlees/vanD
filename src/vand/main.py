#!/usr/bin/env python3

import asyncio
import logging
from typing import Union

import click


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


async def async_main(
    debug: bool,
    config: str,
) -> int:
    return 0


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--debug",
    is_flag=True,
    callback=_handle_debug,
    show_default=True,
    help="Turn on debug logging",
)
@click.argument("config", nargs=1)
@click.pass_context
def main(
    ctx: click.Context,
    **kwargs,
) -> None:
    """vanD: All your RV monitoring needs"""
    ctx.exit(asyncio.run(async_main(**kwargs)))


if __name__ == "__main__":
    main()

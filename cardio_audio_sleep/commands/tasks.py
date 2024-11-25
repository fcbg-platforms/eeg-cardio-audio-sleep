from __future__ import annotations

import click
import numpy as np

from .. import set_log_level
from ..tasks import asynchronous as asynchronous_task
from ..tasks import baseline as baseline_task
from ..tasks import isochronous as isochronous_task
from ..tasks import synchronous as synchronous_task
from ..tasks._config import BASELINE_DURATION, N_OMISSION, N_SOUND
from ._utils import ch_name_ecg, stream, verbose


@click.command()
@click.option(
    "--duration",
    prompt="Duration of the baseline (seconds)",
    help="Duration of the baseline in seconds.",
    type=float,
    default=BASELINE_DURATION,
)
@verbose
def baseline(duration: float, verbose: str) -> None:
    """Run a baseline task."""
    set_log_level(verbose)
    baseline_task(duration)


@click.command()
@click.option(
    "--delay",
    prompt="Delay between 2 stimulus (seconds)",
    help="Delay between 2 stimulus in seconds.",
    type=float,
)
@verbose
def isochronous(delay: float, verbose: str) -> None:
    """Run an isochronous task."""
    set_log_level(verbose)
    isochronous_task(delay)


@click.command()
@click.option(
    "--delays",
    help="Min and max delays between 2 stimuli in seconds.",
    type=(float, float),
    default=(0.5, 1.5),
    show_default=True,
)
@verbose
def asynchronous(delays: tuple[float, float], verbose: str) -> None:
    """Run an asynchronous task."""
    set_log_level(verbose)
    # create random peak position based on the min/max delays requested
    if delays[0] <= 0:
        raise ValueError("The minimum delay must be strictly positive.")
    if delays[1] <= 0:
        raise ValueError("The maximum delay must be strictly positive.")
    rng = np.random.default_rng()
    delays = rng.uniform(low=delays[0], high=delays[1], size=N_SOUND + N_OMISSION - 1)
    peaks = np.hstack(([0], np.cumsum(delays)))
    asynchronous_task(peaks)


@click.command()
@stream
@ch_name_ecg
@verbose
def synchronous(stream: str, ch_name_ecg: str, verbose: str) -> None:
    """Run a synchronous task."""
    set_log_level(verbose)
    synchronous_task(stream, ch_name_ecg)

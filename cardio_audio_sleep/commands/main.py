from __future__ import annotations

import time
from itertools import cycle

import click
import numpy as np

from .. import set_log_level
from ..tasks import asynchronous as asynchronous_task
from ..tasks import baseline as baseline_task
from ..tasks import isochronous as isochronous_task
from ..tasks import synchronous as synchronous_task
from ..tasks._config import BASELINE_DURATION, INTER_BLOCK_DELAY, ConfigRepr
from ..utils.blocks import _BLOCKS, generate_blocks_sequence
from ..utils.logs import logger
from ._utils import ch_name_ecg, fq_deviant, fq_target, stream, verbose
from .tasks import asynchronous, baseline, isochronous, synchronous
from .testing import test_detector, test_sequence, test_triggers


@click.group()
def run():
    """Entry point to start the tasks."""
    config = ConfigRepr()
    click.echo(config)


@click.command()
@click.option(
    "--n-blocks", prompt="Number of blocks", help="Number of blocks.", type=int
)
@stream
@ch_name_ecg
@fq_target
@fq_deviant
@verbose
def paradigm(
    n_blocks: int,
    stream: str,
    ch_name_ecg: str,
    target: float,
    deviant: float,
    verbose: str,
) -> None:
    """Run the paradigm, alternating between blocks."""
    set_log_level(verbose)
    if n_blocks <= 0:
        raise ValueError(f"Number of blocks must be positive. '{n_blocks}' is invalid.")
    # prepare mapping between function and block name
    mapping_func = {
        "baseline": baseline_task,
        "isochronous": isochronous_task,
        "asynchronous": asynchronous_task,
        "synchronous": synchronous_task,
    }
    assert len(set(mapping_func) - set(_BLOCKS)) == 0  # sanity-check
    # prepare mapping between argument and block name
    mapping_args = {
        "baseline": [BASELINE_DURATION],
        "isochronous": [None],
        "asynchronous": [None],
        "synchronous": [stream, ch_name_ecg],
    }
    assert len(set(mapping_args) - set(_BLOCKS)) == 0
    # prepare mapping between keyword argument and block name, including target and
    # deviant cycling frequencis
    targets = cycle([target, deviant])
    deviants = cycle([deviant, target])
    # overwrite the same variables
    target = next(targets)
    deviant = next(deviants)
    mapping_kwargs = {
        "baseline": {},
        "isochronous": {"target": target, "deviant": deviant},
        "asynchronous": {"target": target, "deviant": deviant},
        "synchronous": {"target": target, "deviant": deviant},
    }
    assert len(set(mapping_kwargs) - set(_BLOCKS)) == 0  # sanity-check

    # execute paradigm loop
    blocks = list()
    while len(blocks) < n_blocks:
        blocks.append(generate_blocks_sequence(blocks))
        logger.info("Running block %i / %i: %s.", len(blocks), n_blocks, blocks[-1])
        start = time.time()
        result = mapping_func[blocks[-1]](
            *mapping_args[blocks[-1]], **mapping_kwargs[blocks[-1]]
        )
        end = time.time()
        logger.info("Block '%s' took %.3f seconds.", blocks[-1], end - start)
        # prepare arguments for future blocks if we just ran a synchronous block
        if result is not None:
            # sanity-check
            assert blocks[-1] == "synchronous"
            assert isinstance(result, np.ndarray)
            assert result.ndim == 1
            assert result.size != 0
            mapping_args["baseline"][0] = end - start
            mapping_args["asynchronous"][0] = result
            delay = np.median(np.diff(result))
            mapping_args["isochronous"][0] = delay
            logger.info(
                "Median delay between respiration peaks set to %.3f seconds.", delay
            )
        # prepare keyword argument for future blocks if we just ran 4 blocks
        if len(blocks) % 4 == 0:
            logger.info("Cycling target and deviant frequencies.")
            target = next(targets)
            deviant = next(deviants)
            for key, elt in mapping_kwargs.items():
                if key == "baseline":
                    continue
                elt["target"] = target
                elt["deviant"] = deviant
        time.sleep(INTER_BLOCK_DELAY)
    logger.info("Paradigm complete.")


run.add_command(baseline)
run.add_command(isochronous)
run.add_command(asynchronous)
run.add_command(synchronous)
run.add_command(paradigm)
run.add_command(test_detector)
run.add_command(test_sequence)
run.add_command(test_triggers)

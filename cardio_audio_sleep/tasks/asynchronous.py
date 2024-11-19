from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from stimuli.time import Clock, sleep

from ..detector import _BUFSIZE
from ..utils._checks import check_type
from ..utils._docs import fill_doc
from ..utils.logs import logger
from ._config import (
    BACKEND,
    OUTLIER_PERC,
    SOUND_DURATION,
    TARGET_DELAY,
    TRIGGER_TASKS,
    TRIGGERS,
)
from ._utils import create_sound, create_trigger, generate_sequence

if BACKEND == "ptb":
    import psychtoolbox as ptb

if TYPE_CHECKING:
    from numpy.typing import NDArray


@fill_doc
def asynchronous(peaks: NDArray[np.float64]) -> None:
    """Asynchronous blocks where a synchronous sequence is repeated.

    Parameters
    ----------
    %(peaks)s
    """  # noqa: D401
    check_type(peaks, (np.ndarray,), "peaks")
    if peaks.ndim != 1:
        raise ValueError("The peaks array must be one-dimensional.")
    logger.info("Starting asynchronous block.")
    # create sound stimuli, trigger, sequence and clock
    sound = create_sound()
    trigger = create_trigger()
    sequence = generate_sequence()
    clock = Clock()
    # generate delays between peaks
    rng = np.random.default_rng()
    delays = np.diff(peaks)
    edges = np.percentile(delays, [OUTLIER_PERC, 100 - OUTLIER_PERC])
    delays = delays[np.where((edges[0] < delays) & (delays < edges[1]))]
    delays = rng.choice(delays, size=sequence.size, replace=True)
    # main loop
    sleep(_BUFSIZE)  # fake a buffer filling
    counter = 0
    trigger.signal(TRIGGER_TASKS["asynchronous"][0])
    while counter <= sequence.size - 1:
        start = clock.get_time()
        if sequence[counter] == TRIGGERS["sound"]:
            sound.play(
                when=ptb.GetSecs() + TARGET_DELAY if BACKEND == "ptb" else TARGET_DELAY
            )
            logger.debug(
                "[sound/trigger] %i in %.3f ms.", sequence[counter], TARGET_DELAY
            )
        else:
            logger.debug(
                "[omission/trigger] %i in %.3f ms.", sequence[counter], TARGET_DELAY
            )
        logger.debug("Triggering %i in %.2f ms.", sequence[counter], TARGET_DELAY)
        sleep(TARGET_DELAY)
        trigger.signal(sequence[counter])
        logger.info("Stimulus %i / %i complete.", counter + 1, sequence.size)
        # note that if the delays are too short, the value 'wait' could end up negative
        # which (1) makes no sense and (2) would raise in the sleep function.
        wait = start + delays[counter] - clock.get_time()
        sleep(wait)
        counter += 1
    # wait for the last sound to finish
    if wait < 1.1 * SOUND_DURATION:
        sleep(1.1 * SOUND_DURATION - wait)
    trigger.signal(TRIGGER_TASKS["asynchronous"][1])
    logger.info("Asynchronous block complete.")

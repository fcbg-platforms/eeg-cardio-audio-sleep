from __future__ import annotations

from stimuli.time import Clock, sleep

from ..detector import _BUFSIZE
from ..utils._checks import check_type
from ..utils._docs import fill_doc
from ..utils.logs import logger
from ._config import BACKEND, SOUND_DURATION, TARGET_DELAY, TRIGGER_TASKS
from ._utils import create_sound, create_trigger, generate_sequence, get_event_name

if BACKEND == "ptb":
    import psychtoolbox as ptb


@fill_doc
def isochronous(delay: float) -> None:
    """Isochronous auditory stimulus.

    Parameters
    ----------
    delay : float
        Delay between 2 stimuli in seconds.
    """  # noqa: D401
    check_type(delay, ("numeric",), "delay")
    if delay <= 0:
        raise ValueError("The delay must be strictly positive.")
    logger.info("Starting isochronous block.")
    # create sound stimuli, trigger, sequence and clock
    sound = create_sound(backend=BACKEND)
    trigger = create_trigger()
    sequence = generate_sequence()
    clock = Clock()
    # main loop
    sleep(_BUFSIZE)  # fake a buffer filling
    counter = 0
    trigger.signal(TRIGGER_TASKS["isochronous"][0])
    while counter <= sequence.size - 1:
        event = get_event_name(sequence[counter])
        start = clock.get_time()
        if event == "sound":
            sound.play(
                when=ptb.GetSecs() + TARGET_DELAY if BACKEND == "ptb" else TARGET_DELAY
            )
        logger.debug(
            "[%s/trigger] %i in %.3f ms.", event, sequence[counter], TARGET_DELAY
        )
        sleep(TARGET_DELAY)
        trigger.signal(sequence[counter])
        logger.info("(%s) %i / %i complete.", event, counter + 1, sequence.size)
        # note that if 'delay' is too short, the value 'wait' could end up negative
        # which (1) makes no sense and (2) would raise in the sleep function.
        wait = start + delay - clock.get_time()
        sleep(wait)
        counter += 1
    # wait for the last sound to finish
    if wait < 1.1 * SOUND_DURATION:
        sleep(1.1 * SOUND_DURATION - wait)
    trigger.signal(TRIGGER_TASKS["isochronous"][1])
    logger.info("Isochronous block complete.")

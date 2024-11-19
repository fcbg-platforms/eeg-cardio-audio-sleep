from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from mne_lsl.lsl import local_clock
from stimuli.time import sleep

from .._config import RECORDER, RECORDER_PATH
from ..detector import Detector
from ..utils._docs import fill_doc
from ..utils.logs import logger
from ._config import (
    BACKEND,
    ECG_DISTANCE,
    ECG_HEIGHT,
    ECG_PROMINENCE,
    SOUND_DURATION,
    TARGET_DELAY,
    TRIGGER_TASKS,
    TRIGGERS,
)
from ._utils import create_sounds, create_trigger, generate_sequence

if BACKEND == "ptb":
    import psychtoolbox as ptb

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from psychopy.sound.backend_ptb import SoundPTB
    from stimuli.audio import Tone
    from stimuli.trigger._base import BaseTrigger


@fill_doc
def synchronous(
    stream_name: str,
    ecg_ch_name: str,
    *,
    target: float,
    deviant: float,
) -> NDArray[np.float64]:
    """Synchronous auditory stimulus with the respiration peak signal.

    Parameters
    ----------
    %(stream_name)s
    %(ecg_ch_name)s
    %(fq_target)s
    %(fq_deviant)s

    Returns
    -------
    peaks : array of shape (n_peaks,)
        The detected cardiac R-peak timings in seconds.
    """  # noqa: D401
    logger.info("Starting synchronous block.")
    # create sound stimuli, trigger, sequence
    sounds = create_sounds()
    trigger = create_trigger()
    sequence = generate_sequence(target, deviant)
    # the sequence, sound and trigger generation validates the trigger dictionary, thus
    # we can safely map the target and deviant frequencies to their corresponding
    # trigger values and sounds.
    stimulus = {
        TRIGGERS[f"target/{target}"]: sounds[str(target)],
        TRIGGERS[f"deviant/{deviant}"]: sounds[str(deviant)],
    }
    # create detector
    detector = Detector(
        stream_name=stream_name,
        ecg_ch_name=ecg_ch_name,
        ecg_height=ECG_HEIGHT,
        ecg_distance=ECG_DISTANCE,
        ecg_prominence=ECG_PROMINENCE,
        detrend=True,
        viewer=False,
        recorder=RECORDER,
    )
    # main loop
    counter = 0
    peaks = []
    trigger.signal(TRIGGER_TASKS["synchronous"][0])
    while counter <= sequence.size - 1:
        pos = detector.new_peak()
        if pos is None:
            continue
        success = _deliver_stimuli(pos, sequence[counter], stimulus, trigger)
        if not success:
            continue
        counter += 1
        logger.info("Stimulus %i / %i complete.", counter, sequence.size)
        peaks.append(pos)
    # wait for the last sound to finish
    sleep(1.1 * SOUND_DURATION)
    trigger.signal(TRIGGER_TASKS["synchronous"][1])
    logger.info("Synchronous block complete.")
    if detector.recorder is not None:
        detector.recorder.save(RECORDER_PATH)
    return np.array(peaks)


def _deliver_stimuli(
    pos: float, elt: int, stimulus: dict[int, SoundPTB | Tone], trigger: BaseTrigger
) -> bool:
    """Deliver precisely a sound and its trigger."""
    wait = pos + TARGET_DELAY - local_clock()
    if wait <= 0.015:  # headroom to schedule, buffer and play the sound.
        if wait <= 0:
            logger.info(
                "Skipping bad detection/triggering, too late by %.3f ms.", -wait * 1000
            )
        else:
            logger.info(
                "Skipping sound delivery, %.3f ms remaining to buffer and play is too "
                "short.",
                wait * 1000,
            )
        return False
    stimulus.get(elt).play(when=ptb.GetSecs() + wait if BACKEND == "ptb" else wait)
    logger.debug("Triggering %i in %.3f ms.", elt, wait * 1000)
    sleep(wait)
    trigger.signal(elt)
    return True

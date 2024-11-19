from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING

import numpy as np
from stimuli.trigger import MockTrigger, ParallelPortTrigger

from ..trigger import SerialTrigger
from ..utils._checks import check_type, check_value, ensure_int
from ..utils._docs import fill_doc
from ..utils.logs import logger, warn
from ._config import (
    BLOCKSIZE,
    DEVICE,
    EDGE_PERC,
    N_OMISSION,
    N_SOUND,
    SOUND_DURATION,
    SOUND_FREQUENCY,
    TRIGGER_ARGS,
    TRIGGER_TYPE,
    TRIGGERS,
)

if TYPE_CHECKING:
    from numpy.testing import NDArray
    from psychopy.sound.backend_ptb import SoundPTB
    from stimuli.audio import Tone
    from stimuli.trigger._base import BaseTrigger


@fill_doc
def create_sound(*, backend: str = "ptb") -> SoundPTB | Tone:
    """Create auditory simuli.

    Parameters
    ----------
    backend : ``"ptb"`` | ``"stimuli"``
        The backend to use for the sound generation.

    Returns
    -------
    sound : SoundPTB | Tone
        The sound to use in the task.
    """
    check_value(backend, ("ptb", "stimuli"), "backend")
    if backend == "ptb":
        if DEVICE is not None:
            from psychopy.sound import setDevice

            setDevice(DEVICE, kind="output")

        from psychopy.sound.backend_ptb import SoundPTB

        sound = SoundPTB(
            value=SOUND_FREQUENCY,
            secs=SOUND_DURATION,
            blockSize=BLOCKSIZE,
            stereo=True,
        )
    elif backend == "stimuli":
        from scipy.signal.windows import hann
        from stimuli.audio import Tone

        sound = Tone(
            frequency=SOUND_FREQUENCY,
            volume=100,
            duration=SOUND_DURATION,
            block_size=BLOCKSIZE,
            device=DEVICE,
        )
        window = hann(sound.times.size)
        sound.window = window
    return sound


def create_trigger() -> BaseTrigger:
    """Create a trigger object.

    Returns
    -------
    trigger : Trigger
        The corresponding trigger object.
    """
    check_type(TRIGGER_TYPE, (str,), "trigger_type")
    check_value(TRIGGER_TYPE, ("arduino", "lpt", "serial", "mock"), "TRIGGER_TYPE")
    check_type(TRIGGER_ARGS, (str, "int-like", None), "TRIGGER_ARGS")
    if TRIGGER_TYPE == "arduino":
        if TRIGGER_ARGS is not None:
            raise ValueError(
                "The 'arduino' trigger does not accept any arguments. Set "
                "'TRIGGER_ARGS' to None."
            )
        trigger = ParallelPortTrigger("arduino", delay=10)
    elif TRIGGER_TYPE == "lpt":
        trigger = ParallelPortTrigger(TRIGGER_ARGS, delay=10)
    elif TRIGGER_TYPE == "serial":
        trigger = SerialTrigger(TRIGGER_ARGS)
    elif TRIGGER_TYPE == "mock":
        if TRIGGER_ARGS is not None:
            raise ValueError(
                "The 'mock' trigger does not accept any arguments. Set "
                "'TRIGGER_ARGS' to None."
            )
        trigger = MockTrigger()
    return trigger


@fill_doc
def generate_sequence(
    *,
    edge_perc: int | float = EDGE_PERC,
    max_iter: int = 500,
    on_diverge: str = "warn",
    triggers: dict[str, int] = TRIGGERS,
) -> NDArray[np.int32]:
    """Generate a random sequence of target and omission.

    Parameters
    ----------
    edge_perc : int | float
        Percentage of the total number of elements that have to be targets at
        the beginning and at the end of the sequence.
    max_iter : int
        Maximum number of iteration to randomize the sequence.
    on_diverge : str
        Either 'warn' to log an error message or 'raise' to raise a RuntimeError when
        the randomization does not converge within the maximum number of iteration
        allowed.
    %(triggers_dict)s

    Returns
    -------
    sequence : array of int
        The sequence of stimuli, with the target and omission sounds ordered.
    """
    n_sound = ensure_int(N_SOUND, "N_SOUND")
    n_omission = ensure_int(N_OMISSION, "N_OMISSION")
    check_type(edge_perc, ("numeric",), "edge_perc")
    if not (0 <= edge_perc <= 100):
        raise ValueError(
            "Argument 'edge_perc' must be a valid percentage between 0 and 100. "
            f"Provided '{edge_perc}%' is invalid."
        )
    max_iter = ensure_int(max_iter, "max_iter")
    if max_iter <= 0:
        raise ValueError(
            "Argument 'max_iter' must be a strictly positive integer. "
            f"Provided '{max_iter}' is invalid."
        )
    check_type(on_diverge, (str,), "on_diverge")
    check_value(on_diverge, ("warn", "raise"), "on_diverge")
    # retrieve trigger values
    logger.debug(
        "Generating a sequence of %i sound and %i omission, using %s for sound and %s "
        "for omission.",
        n_sound,
        n_omission,
        TRIGGERS["sound"],
        TRIGGERS["omission"],
    )
    # pseudo-randomize the sequence
    n_edge = np.ceil(edge_perc * (n_sound + n_omission) / 100).astype(int)
    start = [TRIGGERS["sound"]] * n_edge
    middle = [TRIGGERS["sound"]] * (n_sound - 2 * n_edge) + [
        TRIGGERS["omission"]
    ] * n_omission
    end = [TRIGGERS["sound"]] * n_edge
    rng = np.random.default_rng()
    rng.shuffle(middle)
    iter_ = 0
    while True:
        groups = [(n, list(group)) for n, group in groupby(middle)]
        if all(
            len(group[1]) == 1 for group in groups if group[0] == TRIGGERS["omission"]
        ):
            converged = True
            break
        if max_iter < iter_:
            msg = "Randomize sequence generation could not converge."
            if on_diverge == "warn":
                warn(msg)
                converged = False
                break
            else:
                raise RuntimeError(msg)
        for i, (n, group) in enumerate(groups):
            if n == TRIGGERS["sound"] or len(group) == 1:
                continue
            # find the longest group of TRIGGERS['sound']
            idx = np.argmax(
                [len(g) if n == TRIGGERS["sound"] else 0 for n, g in groups]
            )
            pos_sound = sum(len(g) for k, (_, g) in enumerate(groups) if k < idx)
            pos_sound = pos_sound + len(groups[idx][1]) // 2  # center
            # find position of current group
            pos_omission = sum(len(g) for k, (_, g) in enumerate(groups) if k < i)
            # swap first element from omissions with center of group of sounds
            middle[pos_sound], middle[pos_omission] = (
                middle[pos_omission],
                middle[pos_sound],
            )
            break
        iter_ += 1
    sequence = start + middle + end
    # sanity-checks
    if converged:
        assert all(len(group) == 1 for n, group in groups if n == TRIGGERS["omission"])
        assert not any(
            middle[i - 1] == middle[i] == TRIGGERS["omission"]
            for i in range(1, len(middle))
        )
    assert len(sequence) == n_sound + n_omission
    assert TRIGGERS["omission"] not in start
    assert TRIGGERS["omission"] not in end
    return np.array(sequence, dtype=np.int32)

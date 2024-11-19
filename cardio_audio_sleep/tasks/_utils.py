from __future__ import annotations

import re
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
    N_DEVIANT,
    N_TARGET,
    SOUND_DURATION,
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
def _check_triggers(*, triggers: dict[str, int] = TRIGGERS) -> None:
    """Check that the trigger dictionary is correctly formatted.

    Parameters
    ----------
    %(triggers_dict)s
    """
    pattern = re.compile(r"^\b(target|deviant)\b\/\d+(\.\d+)+$")
    for elt in triggers:
        check_type(elt, (str,), "trigger-key")
        if not re.fullmatch(pattern, elt):
            raise ValueError(
                "The trigger names must be in the format 'name/frequency', "
                "with name set to 'target' or 'deviant' and frequency as float, but "
                f"got '{elt}' with is invalid."
            )


@fill_doc
def _ensure_valid_frequencies(
    frequencies: dict[str, float | int], *, triggers: dict[str, int] = TRIGGERS
) -> dict[str, float]:
    """Check that the frequencies are valid.

    Parameters
    ----------
    frequencies : dict
        Dictionary of frequency name and value.
    %(triggers_dict)s

    Returns
    -------
    frequencies : dict
        Dictionary of frequency name and value, cast to float.
    """
    check_type(frequencies, (dict,), "frequencies")
    _check_triggers()
    for name, value in frequencies.items():
        check_type(value, ("numeric",), name)
        if value <= 0:
            raise ValueError(
                f"The {name} frequency must be strictly positive. Provided {value} is "
                "invalid."
            )
        value = float(value)  # ensure float
        if f"{name}/{value}" not in triggers:
            raise ValueError(
                f"The {name} frequency '{value}' is not in the trigger dictionary."
            )
        frequencies[name] = value
    return frequencies


@fill_doc
def create_sounds(
    *, triggers: dict[str, int] = TRIGGERS, backend: str = "ptb"
) -> dict[str, SoundPTB | Tone]:
    """Create auditory simuli.

    Parameters
    ----------
    %(triggers_dict)s
    backend : ``"ptb"`` | ``"stimuli"``
        The backend to use for the sound generation.

    Returns
    -------
    sounds : dict
        The sounds to use in the task, with the keys as sound frequency (str) and the
        values as the corresponding SoundPTB or Tone object.
    """
    _check_triggers(triggers=triggers)
    frequencies = set(elt.split("/")[1] for elt in triggers)
    check_value(backend, ("ptb", "stimuli"), "backend")
    if backend == "ptb":
        if DEVICE is not None:
            from psychopy.sound import setDevice

            setDevice(DEVICE, kind="output")

        from psychopy.sound.backend_ptb import SoundPTB

        sounds = {
            frequency: SoundPTB(
                value=float(frequency),
                secs=SOUND_DURATION,
                blockSize=BLOCKSIZE,
                stereo=True,
            )
            for frequency in frequencies
        }
    elif backend == "stimuli":
        from scipy.signal.windows import hann
        from stimuli.audio import Tone

        sounds = {
            frequency: Tone(
                frequency=float(frequency),
                volume=100,
                duration=SOUND_DURATION,
                block_size=BLOCKSIZE,
                device=DEVICE,
            )
            for frequency in frequencies
        }
        n_samples = sounds[frequencies[0]].times.size
        assert all(sound.times.size == n_samples for sound in sounds)  # sanity-check
        window = hann(n_samples)
        for sound in sounds.values():
            sound.window = window
    return sounds


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
    target: float,
    deviant: float,
    *,
    edge_perc: int | float = EDGE_PERC,
    max_iter: int = 500,
    on_diverge: str = "warn",
    triggers: dict[str, int] = TRIGGERS,
) -> NDArray[np.int32]:
    """Generate a random sequence of target and deviant stimuli.

    Parameters
    ----------
    %(fq_target)s
    %(fq_deviant)s
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
        The sequence of stimuli, with the target and deviant sounds randomly ordered.
    """
    n_target = ensure_int(N_TARGET, "N_TARGET")
    n_deviant = ensure_int(N_DEVIANT, "N_DEVIANT")
    frequencies = _ensure_valid_frequencies(
        {"target": target, "deviant": deviant}, triggers=triggers
    )
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
    trigger_target = triggers[f"target/{frequencies['target']}"]
    trigger_deviant = triggers[f"deviant/{frequencies['deviant']}"]
    logger.debug(
        "Generating a sequence of %i target and %i deviant stimuli, using %s for "
        "target and %s for deviant.",
        n_target,
        n_deviant,
        trigger_target,
        trigger_deviant,
    )
    # pseudo-randomize the sequence
    n_edge = np.ceil(edge_perc * (n_target + n_deviant) / 100).astype(int)
    start = [trigger_target] * n_edge
    middle = [trigger_target] * (n_target - 2 * n_edge) + [trigger_deviant] * n_deviant
    end = [trigger_target] * n_edge
    rng = np.random.default_rng()
    rng.shuffle(middle)
    iter_ = 0
    while True:
        groups = [(n, list(group)) for n, group in groupby(middle)]
        if all(len(group[1]) == 1 for group in groups if group[0] == trigger_deviant):
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
            if n == trigger_target or len(group) == 1:
                continue
            # find the longest group of TRIGGERS['sound']
            idx = np.argmax([len(g) if n == trigger_target else 0 for n, g in groups])
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
        assert all(len(group) == 1 for n, group in groups if n == trigger_deviant)
        assert not any(
            middle[i - 1] == middle[i] == trigger_deviant for i in range(1, len(middle))
        )
    assert len(sequence) == n_target + n_deviant
    assert trigger_deviant not in start
    assert trigger_deviant not in end
    return np.array(sequence, dtype=np.int32)

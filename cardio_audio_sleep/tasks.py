"""Tasks functions."""

from itertools import groupby
import math
import random
from typing import Union

from bsl.triggers._trigger import _Trigger
import numpy as np
from numpy.typing import ArrayLike
from psychopy.clock import wait
from psychopy.sound.backend_ptb import SoundPTB as Sound
import psychtoolbox as ptb

from . import logger
from .detector import Detector
from .utils._checks import _check_type, _check_value


BLOCK_SIZE = 255
OMISSIONS = 51
EDGE_PERC = 5
TRIGGERS = dict(sound=1, omission=2, start=10, stop=11)


def synchronous(
        trigger,
        sequence: ArrayLike,
        stream_name: str,
        ecg_ch_name: str,
        peak_height_perc: Union[int, float],
        peak_prominence: Union[int, float]
        ):
    """
    Synchronous block where sounds are sync to the heartbeat.

    Parameters
    ----------
    trigger :
    sequence : array
        Sequence of stimulus/omissions (of length BLOCK_SIZE if complete).
        1 corresponds to a stound stimulus. 2 corresponds to an omission.
    """
    _check_type(trigger, _Trigger, 'trigger')
    sequence = _check_sequence(sequence)

    # Create sound stimuli
    sound = Sound(value=1000, secs=0.1, stereo=True, volume=1.0, blockSize=32,
                  preBuffer=-1, hamming=True)

    # Create peak detector
    detector = Detector(
        stream_name, ecg_ch_name, duration_buffer=5,
        peak_height_perc=peak_height_perc, peak_prominence=peak_prominence)
    detector.prefill_buffer()

    # Create counter
    counter = 0

    # Task loop
    trigger.signal(TRIGGERS['start'])

    while counter <= len(sequence) - 1:
        detector.update_loop()
        pos = detector.new_peaks()
        if pos is not None:
            # compute where we are relative to the r-peak
            delay = detector.timestamps_buffer[-1] \
                - detector.timestamps_buffer[pos]
            # sound
            if sequence[counter] == 1:
                sound.play(ptb.GetSecs() + 0.05 - delay)
            # trigger
            wait(0.05 - delay, hogCPUperiod=1)
            trigger.signal(sequence[counter])
            # next
            counter += 1

    trigger.signal(TRIGGERS['stop'])


def isochronous(
        trigger,
        sequence: ArrayLike,
        bpm: Union[int, float]
        ):
    """
    Isochronous block where sounds are delivered at a fix interval.

    Parameters
    ----------
    trigger :
    sequence : array
        Sequence of stimulus/omissions (of length BLOCK_SIZE if complete).
        1 corresponds to a stound stimulus. 2 corresponds to an omission.
    bpm : float
        Mean heartbeat measured during the last synchronous task (in bpm).
    """
    _check_type(trigger, _Trigger, 'trigger')
    sequence = _check_sequence(sequence)
    _check_type(bpm, ('numeric', ), 'bpm')
    if bpm <= 0:
        raise ValueError(
            "Argument 'bpm' should be a strictly positive number. "
            f"Provided: '{bpm}' beats per minute.")

    # Create sound stimuli
    sound = Sound(value=1000, secs=0.1, stereo=True, volume=1.0, blockSize=32,
                  preBuffer=-1, hamming=True)

    # Convert heartbeat from BPM to inter-stimulus delay.
    delay = 1 / (bpm / 60)  # seconds
    delay -= 0.2  # from sound scheduling

    # Create counter
    counter = 0

    # Task loop
    trigger.signal(TRIGGERS['start'])

    while counter <= len(sequence) - 1:
        # stimuli
        if sequence[counter] == 1:
            sound.play(ptb.GetSecs() + 0.2)
        # trigger
        wait(0.2, hogCPUperiod=1)
        trigger.signal(sequence[counter])

        # next
        counter += 1
        wait(delay)

    trigger.signal(TRIGGERS['stop'])


def asynchronous(
        trigger,
        sequence: ArrayLike,
        sequence_timings: ArrayLike
        ):
    """
    Asynchronous block where sounds repeat a sequence from a synchronous task.
    Omissions are randomized (compared to the synchronous task they are
    extracted from.)

    Parameters
    ----------
    trigger :
    sequence : array
        Sequence of stimulus/omissions (of length BLOCK_SIZE if complete).
        1 corresponds to a stound stimulus. 2 corresponds to an omission.
    sequence_timings : array
        Array of length BLOCK_SIZE containing the timing at which the stimulus
        was delivered.
    """
    _check_type(trigger, _Trigger, 'trigger')
    sequence = _check_sequence(sequence)
    sequence_timings = _check_sequence_timings(sequence_timings, sequence)

    # Create sound stimuli
    sound = Sound(value=1000, secs=0.1, stereo=True, volume=1.0, blockSize=32,
                  preBuffer=-1, hamming=True)

    # Compute delays
    delays = np.diff(sequence_timings)  # a[i+1] - a[i]
    delays -= 0.2  # from sound scheduling
    assert all(0 < delay for delay in delays)  # sanity-check

    # Create counter
    counter = 0

    # Task loop
    trigger.signal(TRIGGERS['start'])

    while counter <= len(sequence) - 1:
        # stimuli
        if sequence[counter] == 1:
            sound.play(ptb.GetSecs() + 0.2)
        # trigger
        wait(0.2, hogCPUperiod=1)
        trigger.signal(sequence[counter])

        # next
        if counter == len(sequence) - 1:
            break  # no more delays since it was the last stimuli
        wait(delays[counter])
        counter += 1

    trigger.signal(TRIGGERS['stop'])


def _check_sequence(
        sequence: ArrayLike
        ):
    """
    Checks that the sequence is valid. Copies the sequence.
    """
    _check_type(sequence, (list, tuple, np.ndarray), 'sequence')
    if isinstance(sequence, (list, tuple)):
        sequence = np.array(sequence)
    elif len(sequence.shape) != 1:
        raise ValueError(
            "Argument 'sequence' should be a 1D iterable and not a "
            f"{len(sequence.shape)}D iterable. ")

    valids = (TRIGGERS['sound'], TRIGGERS['omission'])
    if any(elt not in valids for elt in sequence):
        raise ValueError(
            "Unknown value within 'sequence'. All elements should be among "
            f"'{valids}'.")

    logger.info('Provided sequence contains {sequence.size} elements.')

    return sequence


def _check_sequence_timings(
        sequence_timings: ArrayLike,
        sequence: ArrayLike
        ):
    """
    Checks that the sequence timings are valid. Copies the sequence.
    """
    _check_type(sequence_timings, (list, tuple, np.ndarray),
                'sequence_timings')
    if isinstance(sequence_timings, (list, tuple)):
        sequence_timings = np.array(sequence_timings)
    elif len(sequence_timings.shape) != 1:
        raise ValueError(
            "Argument 'sequence_timings' should be a 1D iterable and not a "
            f"{len(sequence_timings.shape)}D iterable. ")

    if sequence.size != sequence_timings.size:
        raise ValueError(
            "Arguments 'sequence' and 'sequence_timings' did not have the "
            "same number of elements.")

    if any(elt < 0 for elt in sequence_timings):
        raise ValueError(
            "All sequence timings should be strictly positive integers, "
            "except the first timing equal to 0.")

    if sequence_timings[0] != 0:
        sequence_timings -= sequence_timings[0]

    return sequence_timings


def generate_sequence(
        size: int = BLOCK_SIZE,
        omissions: int = OMISSIONS,
        edge_perc: Union[int, float] = EDGE_PERC,
        max_iter: int = 500,
        on_diverge: str = 'warn',
        ):
    """
    Creates a valid sequence.
    - 255 sounds / block
    - 20% (51) are omissions

    An omission should not be in the first or last 5%.
    Omissions should not be consecutive.

    Parameters
    ----------
    size : int
        Total number of elements in the sequence.
    omissions : int
        Total number of omissions in the sequence.
    edge_perc : float
        Percentage of the total number of elements that have to be sound at
        the beginning and at the end of the sequence.
    max_iter : int
        Maximum numnber of iteration to randomize the sequence.
    on_diverge : str
        Either 'warn' to log an error message or 'raise' to raise a
        RuntimeError when the randomization does not converge within the
        maximum number of iteration allowed.
    """
    _check_type(size, ('int', ), 'size')
    _check_type(omissions, ('int', ), 'omissions')
    _check_type(edge_perc, ('numeric', ), 'edge_perc')
    _check_type(max_iter, ('int', ), 'max_iter')
    _check_value(on_diverge, ('warn', 'raise'), 'on_diverge')
    if size <= 0:
        raise ValueError(
            "Argument 'size' must be a strictly positive integer. "
            f"Provided: '{size}'.")
    if omissions <= 0:
        raise ValueError(
            "Argument 'omissions' must be a strictly positive integer. "
            f"Provided: '{omissions}'.")
    if not (0 <= edge_perc <= 100):
        raise ValueError(
            "Argument 'edge_perc' must be a valid percentage between 0 and "
            f"100. Provided {edge_perc}%.")
    if max_iter <= 0:
        raise ValueError(
            "Argument 'max_iter' must be a strictly positive integer. "
            f"Provided: '{max_iter}'.")

    n_edge = math.ceil(edge_perc * size / 100)
    start = [TRIGGERS['sound']] * n_edge

    middle = [TRIGGERS['sound']] * (size - omissions - 2 * n_edge)
    middle += [TRIGGERS['omission']] * omissions
    random.shuffle(middle)
    iter_ = 0
    while True:
        groups = [(n, list(group)) for n, group in groupby(middle)]

        if all(len(group[1]) == 1
               for group in groups if group[0] == TRIGGERS['omission']):
            converged = True
            break

        if max_iter < iter_:
            msg = "Randomize sequence generation could not converge."
            if on_diverge == 'warn':
                logger.warning(msg)
                converged = False
            else:
                raise RuntimeError(msg)
            break

        for i, (n, group) in enumerate(groups):
            if n == TRIGGERS['sound'] or len(group) == 1:
                continue

            # find the longest group of TRIGGERS['sound']
            idx = np.argmax([len(g) if n == TRIGGERS['sound'] else 0
                             for n, g in groups])
            pos_sound = sum(len(g) for k, (_, g) in enumerate(groups)
                            if k < idx)
            pos_sound = pos_sound + len(groups[idx][1]) // 2  # center

            # find position of current group
            pos_omission = sum(len(g) for k, (_, g) in enumerate(groups)
                               if k < i)

            # swap first element from omissions with center of group of sounds
            middle[pos_sound], middle[pos_omission] = \
                middle[pos_omission], middle[pos_sound]

            break

        iter_ += 1

    # sanity-check
    if converged:
        assert all(len(group) == 1
                   for n, group in groups if n == TRIGGERS['omission'])
        assert not any(middle[i-1] == TRIGGERS['omission'] \
                       and middle[i] == TRIGGERS['omission']
                       for i in range(1, len(middle)))

    end = [TRIGGERS['sound']] * n_edge
    return np.array(start + middle + end)

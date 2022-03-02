"""Tasks functions."""

from itertools import groupby
import math
import random
from typing import Union

from bsl.triggers import TriggerDef
import numpy as np
from numpy.typing import ArrayLike
from psychopy.clock import wait
from psychopy.sound.backend_ptb import SoundPTB as Sound
import psychtoolbox as ptb
from pylsl import local_clock

from . import logger
from .detector import Detector
from .utils._checks import _check_type, _check_value


def synchronous(
        trigger,
        tdef,
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
    trigger : Trigger
        A BSL trigger instance.
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - sync_start
            - sound (aligned on sequence)
            - omission (aligned on sequence)
            - sync_stop
    sequence : array
        Sequence of stimulus/omissions (of length BLOCK_SIZE if complete).
        1 corresponds to a stound stimulus. 2 corresponds to an omission.
    stream_name : str
        Name of the LSL stream to connect to.
    ecg_ch_name : str
        Name of the ECG channel in the LSL stream.
    peak_height_perc : float
        Minimum height of the peak expressed as a percentile of the samples in
        the buffer.
    peak_prominence : float
        Minimum peak prominence as defined by scipy.

    Returns
    -------
    sequence_timings : list
        List of timings at which an R-peak occured.
    """
    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)

    # Create sound stimuli
    sound = Sound(value=250, secs=0.1, stereo=True, volume=1.0, blockSize=32,
                  preBuffer=-1, hamming=True)

    # Create peak detector
    detector = Detector(
        stream_name, ecg_ch_name, duration_buffer=3,
        peak_height_perc=peak_height_perc, peak_prominence=peak_prominence)
    detector.prefill_buffer()

    # Create counter
    counter = 0

    # Create containers for sequence timings
    sequence_timings = list()

    # Task loop
    trigger.signal(tdef.sync_start)
    wait(0.1)

    while counter <= len(sequence) - 1:
        detector.update_loop()
        pos = detector.new_peaks()
        if pos is not None:
            # compute where we are relative to the r-peak
            delay = local_clock() - detector.timestamps_buffer[pos]
            # sound
            if sequence[counter] == 1:
                sound.play(when=ptb.GetSecs() + 0.05 - delay)
            # trigger
            wait(0.05 - delay, hogCPUperiod=1)
            trigger.signal(sequence[counter])
            # next
            sequence_timings.append(detector.timestamps_buffer[pos])
            counter += 1

    wait(0.1)
    trigger.signal(tdef.sync_stop)

    return sequence_timings


def isochronous(
        trigger,
        tdef,
        sequence: ArrayLike,
        delay: Union[int, float]
        ):
    """
    Isochronous block where sounds are delivered at a fix interval.

    Parameters
    ----------
    trigger : Trigger
        A BSL trigger instance.
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - iso_start
            - sound (aligned on sequence)
            - omission (aligned on sequence)
            - iso_stop
    sequence : array
        Sequence of stimulus/omissions (of length BLOCK_SIZE if complete).
        1 corresponds to a stound stimulus. 2 corresponds to an omission.
    delay : float
        Delay between 2 stimulus in seconds.
    """
    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)
    _check_type(delay, ('numeric', ), 'delay')
    if delay <= 0:
        raise ValueError(
            "Argument 'delay' should be a strictly positive number. "
            f"Provided: '{delay}' seconds.")
    assert 0.2 < delay  # sanity-check

    # Create sound stimuli
    sound = Sound(value=250, secs=0.1, stereo=True, volume=1.0, blockSize=32,
                  preBuffer=-1, hamming=True)

    # Remove scheduling from delay
    delay -= 0.2

    # Create counter
    counter = 0

    # Task loop
    trigger.signal(tdef.iso_start)
    wait(0.1)

    while counter <= len(sequence) - 1:
        # stimuli
        if sequence[counter] == 1:
            sound.play(when=ptb.GetSecs() + 0.2)
        # trigger
        wait(0.2, hogCPUperiod=1)
        trigger.signal(sequence[counter])

        # next
        counter += 1
        wait(delay)

    wait(0.1)
    trigger.signal(tdef.iso_stop)


def asynchronous(
        trigger,
        tdef,
        sequence: ArrayLike,
        sequence_timings: ArrayLike
        ):
    """
    Asynchronous block where sounds repeat a sequence from a synchronous task.
    Omissions are randomized (compared to the synchronous task they are
    extracted from).

    Parameters
    ----------
    trigger : Trigger
        A BSL trigger instance.
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - async_start
            - sound (aligned on sequence)
            - omission (aligned on sequence)
            - async_stop
    sequence : array
        Sequence of stimulus/omissions (of length BLOCK_SIZE if complete).
        1 corresponds to a stound stimulus. 2 corresponds to an omission.
    sequence_timings : array
        Array of length BLOCK_SIZE containing the timing at which the stimulus
        was delivered.
    """
    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)
    sequence_timings = _check_sequence_timings(sequence_timings, sequence, 0.2)

    # Create sound stimuli
    sound = Sound(value=250, secs=0.1, stereo=True, volume=1.0, blockSize=32,
                  preBuffer=-1, hamming=True)

    # Compute delays
    delays = np.diff(sequence_timings)  # a[i+1] - a[i]
    delays -= 0.2  # from sound scheduling
    assert all(0 < delay for delay in delays)  # sanity-check

    # Create counter
    counter = 0

    # Task loop
    trigger.signal(tdef.async_start)
    wait(0.1)

    while counter <= len(sequence) - 1:
        # stimuli
        if sequence[counter] == 1:
            sound.play(when=ptb.GetSecs() + 0.2)
        # trigger
        wait(0.2, hogCPUperiod=1)
        trigger.signal(sequence[counter])

        # next
        if counter == len(sequence) - 1:
            break  # no more delays since it was the last stimuli
        wait(delays[counter])
        counter += 1

    wait(0.1)
    trigger.signal(tdef.async_stop)


def baseline(
        trigger,
        tdef,
        duration: Union[int, float]
        ):
    """
    Baseline block corresponding to a resting-state recording.

    Parameters
    ----------
    trigger : Trigger
        A BSL trigger instance.
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - baseline_start
            - baseline_stop
    duration : float
        Duration of the resting-state block in seconds.
    """
    _check_tdef(tdef)

    # Task loop
    trigger.signal(tdef.baseline_start)
    wait(duration)
    trigger.signal(tdef.baseline_stop)


def _check_tdef(tdef):
    """
    Checks that the trigger definition contains all the required keys.
    """
    _check_type(tdef, (TriggerDef, ), 'tdef')
    keys = ('sound', 'omission',
            'sync_start', 'sync_stop',
            'iso_start', 'iso_stop',
            'async_start', 'async_stop',
            'baseline_start', 'baseline_stop')
    assert all(hasattr(tdef, attribute) for attribute in keys)


def _check_sequence(
        sequence: ArrayLike,
        tdef
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

    valids = (tdef.sound, tdef.omission)
    if any(elt not in valids for elt in sequence):
        raise ValueError(
            "Unknown value within 'sequence'. All elements should be among "
            f"'{valids}'.")

    logger.info('Provided sequence contains %s elements.', sequence.size)

    return sequence


def _check_sequence_timings(
        sequence_timings: ArrayLike,
        sequence: ArrayLike,
        min_distance: Union[int, float]
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

    if any(elt <= min_distance for elt in np.diff(sequence_timings)):
        raise ValueError(
            "All sequence timings should be separated by at least "
            f"{min_distance} seconds.")

    return sequence_timings


def generate_sequence(
        size: int,
        omissions: int,
        edge_perc: Union[int, float],
        tdef,
        max_iter: int = 500,
        on_diverge: str = 'warn',
        ):
    """
    Creates a valid sequence.
    - 300 sounds / block
    - 20% (60) are omissions

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
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - sound (aligned on sequence)
            - omission (aligned on sequence)
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
    if omissions < 0:
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
    start = [tdef.sound] * n_edge

    middle = [tdef.sound] * (size - omissions - 2 * n_edge)
    middle += [tdef.omission] * omissions
    random.shuffle(middle)
    iter_ = 0
    while True:
        groups = [(n, list(group)) for n, group in groupby(middle)]

        if all(len(group[1]) == 1
               for group in groups if group[0] == tdef.omission):
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
            if n == tdef.sound or len(group) == 1:
                continue

            # find the longest group of TRIGGERS['sound']
            idx = np.argmax([len(g) if n == tdef.sound else 0
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
                   for n, group in groups if n == tdef.omission)
        assert not any(middle[i-1] == middle[i] == tdef.omission
                       for i in range(1, len(middle)))

    end = [tdef.sound] * n_edge
    return np.array(start + middle + end)

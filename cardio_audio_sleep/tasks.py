"""Tasks functions."""

import datetime
from multiprocessing import Queue
from typing import Optional

import numpy as np
import psychtoolbox as ptb
from numpy.typing import ArrayLike
from psychopy.clock import wait

from . import logger
from .utils._checks import (
    _check_sequence,
    _check_sequence_timings,
    _check_tdef,
    _check_type,
)
from .utils._docs import fill_doc


@fill_doc
def synchronous(
    trigger,
    tdef,
    sequence: ArrayLike,
    stream_name: str,
    ecg_ch_name: str,
    peak_height_perc: float,
    peak_prominence: Optional[float],
    peak_width: Optional[float],
    volume: float,
    queue: Optional[Queue] = None,
) -> list:
    """
    Synchronous block where sounds are sync to the heartbeat.

    Parameters
    ----------
    %(trigger)s
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - sync_start
            - sound (aligned on sequence)
            - omission (aligned on sequence)
            - sync_stop
    %(sequence)s
    stream_name : str
        Name of the LSL stream to connect to.
    ecg_ch_name : str
        Name of the ECG channel in the LSL stream.
    peak_height_perc : float
        Minimum height of the peak expressed as a percentile of the samples in
        the buffer.
    peak_prominence : float | None
        Minimum peak prominence as defined by scipy.
    peak_width : float | None
        Minimum peak width expressed in ms. Default to None.
    %(volume)s
    queue : Queue
        Queue where the sequence_timings are stored. If None, this argument is
        ignored.

    Returns
    -------
    sequence_timings : list
        List of timings at which an R-peak occured.
    """
    from .audio import Tone
    from .detector import Detector

    # Create sound stimuli
    sound = Tone(volume, frequency=1000)

    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)

    # Create peak detector
    detector = Detector(
        stream_name,
        ecg_ch_name,
        duration_buffer=4,
        peak_height_perc=peak_height_perc,
        peak_prominence=peak_prominence,
        peak_width=peak_width,
    )
    detector.prefill_buffer()

    # Create counter/timers
    counter = 0

    # Create containers for sequence timings
    sequence_timings = list()

    # Task loop
    trigger.signal(tdef.sync_start)
    wait(0.2, hogCPUperiod=0)

    while counter <= len(sequence) - 1:
        detector.update_loop()
        pos = detector.new_peaks()
        if pos is not None:
            delay = ptb.GetSecs() - detector.timestamps_buffer[pos]
            wait(0.038 - delay, hogCPUperiod=1)  # computer specific delay
            # trigger
            trigger.signal(sequence[counter])
            # sound
            if sequence[counter] == 1:
                sound.play()
            # next
            sequence_timings.append(detector.timestamps_buffer[pos])
            counter += 1
            logger.info("Sound %i/%i delivered.", counter, len(sequence))
            # wait for sound to be delivered before updating again
            # and give CPU time to other processes
            wait(0.1, hogCPUperiod=0)

    wait(1, hogCPUperiod=0)
    trigger.signal(tdef.sync_stop)

    if queue is not None:
        queue.put(sequence_timings)

    return sequence_timings


@fill_doc
def isochronous(
    trigger, tdef, sequence: ArrayLike, delay: float, volume: float
):
    """
    Isochronous block where sounds are delivered at a fix interval.

    Parameters
    ----------
    %(trigger)s
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - iso_start
            - sound (aligned on sequence)
            - omission (aligned on sequence)
            - iso_stop
    %(sequence)s
    delay : float
        Delay between 2 stimulus in seconds.
    %(volume)s
    """
    from .audio import Tone

    # Create sound stimuli
    sound = Tone(volume, frequency=1000)

    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)
    _check_type(delay, ("numeric",), "delay")
    if delay <= 0:
        raise ValueError(
            "Argument 'delay' should be a strictly positive number. "
            f"Provided: '{delay}' seconds."
        )
    assert sound.duration < delay  # sanity-check

    # Create counter
    counter = 0

    # Task loop
    trigger.signal(tdef.iso_start)
    wait(0.2, hogCPUperiod=0)

    while counter <= len(sequence) - 1:
        now = ptb.GetSecs()
        trigger.signal(sequence[counter])
        # stimuli
        if sequence[counter] == 1:
            sound.play()
            logger.info("Sound %i/%i delivered.", counter + 1, len(sequence))
        stim_delay = ptb.GetSecs() - now

        # next
        wait(delay - stim_delay)
        counter += 1

    wait(1, hogCPUperiod=0)
    trigger.signal(tdef.iso_stop)


@fill_doc
def asynchronous(
    trigger,
    tdef,
    sequence: ArrayLike,
    sequence_timings: ArrayLike,
    volume: float,
):
    """
    Asynchronous block where sounds repeat a sequence from a synchronous task.
    Omissions are randomized (compared to the synchronous task they are
    extracted from).

    Parameters
    ----------
    %(trigger)s
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - async_start
            - sound (aligned on sequence)
            - omission (aligned on sequence)
            - async_stop
    %(sequence)s
    sequence_timings : array
        Array of length BLOCK_SIZE containing the timing at which the stimulus
        was delivered.
    %(volume)s
    """
    from .audio import Tone

    # Create sound stimuli
    sound = Tone(volume, frequency=1000)

    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)
    sequence_timings = _check_sequence_timings(
        sequence_timings, sequence, sound.duration
    )

    # Compute delays
    delays = np.diff(sequence_timings)  # a[i+1] - a[i]
    assert all(sound.duration < delay for delay in delays)  # sanity-check

    # Create counter
    counter = 0

    # Task loop
    trigger.signal(tdef.async_start)
    wait(0.2, hogCPUperiod=0)

    while counter <= len(sequence) - 1:
        now = ptb.GetSecs()
        trigger.signal(sequence[counter])
        # stimuli
        if sequence[counter] == 1:
            sound.play()
            logger.info("Sound %i/%i delivered.", counter + 1, len(sequence))
        stim_delay = ptb.GetSecs() - now

        # next
        if counter != len(sequence) - 1:
            wait(delays[counter] - stim_delay)
            counter += 1
        else:
            break  # no more delays since it was the last stimuli

    wait(1, hogCPUperiod=0)
    trigger.signal(tdef.async_stop)


@fill_doc
def baseline(trigger, tdef, duration: float, verbose: bool = True):
    """
    Baseline block corresponding to a resting-state recording.

    Parameters
    ----------
    %(trigger)s
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - baseline_start
            - baseline_stop
    duration : int
        Duration of the resting-state block in seconds.
    verbose : bool
        If True, a timer is logged with the info level every second.
    """
    _check_tdef(tdef)
    _check_type(duration, ("numeric",), "duration")
    if duration <= 0:
        raise ValueError(
            "Argument 'duration' should be a strictly positive number. "
            f"Provided: '{duration}' seconds."
        )
    _check_type(verbose, (bool,), "verbose")

    # Start trigger
    trigger.signal(tdef.baseline_start)

    duration_ = datetime.timedelta(seconds=duration)

    # Counts second instead of using a clock. Less precise, but compatible
    # with a process interruption.
    counter = 0
    while counter < duration:
        counter += 1
        wait(1, hogCPUperiod=0)
        if verbose:
            now = datetime.timedelta(seconds=counter)
            logger.info("Baseline: %s / %s", now, duration_)

    # Stop trigger
    trigger.signal(tdef.baseline_stop)


def inter_block(duration: float, verbose: bool = True):
    """
    Inter-block task-like to wait a specific duration.

    Parameters
    ----------
    duration : int
        Duration of the inter-block in seconds.
    verbose : bool
        If True, a timer is logged with the info level every second.
    """
    _check_type(duration, ("numeric",), "duration")
    if duration <= 0:
        raise ValueError(
            "Argument 'duration' should be a strictly positive number. "
            f"Provided: '{duration}' seconds."
        )
    _check_type(verbose, (bool,), "verbose")

    duration_ = datetime.timedelta(seconds=duration)

    # Counts second instead of using a clock. Less precise, but compatible
    # with a process interruption.
    counter = 0
    while counter < duration:
        counter += 1
        wait(1, hogCPUperiod=0)
        if verbose:
            now = datetime.timedelta(seconds=counter)
            logger.info("Inter-block: %s / %s", now, duration_)

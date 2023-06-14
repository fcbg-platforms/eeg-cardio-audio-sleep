"""Tasks functions."""

import datetime
from multiprocessing import Queue
from pathlib import Path
from typing import Optional

import numpy as np
import psychtoolbox as ptb
from bsl.triggers import TriggerDef
from numpy.typing import ArrayLike
from psychopy.clock import wait
from scipy.signal.windows import tukey

from . import logger
from .config.constants import TONE_FQ
from .triggers import Trigger
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
    tdef: TriggerDef,
    sequence: ArrayLike,
    stream_name: str,
    ecg_ch_name: str,
    peak_height_perc: float,
    peak_prominence: Optional[float],
    peak_width: Optional[float],
    volume: float,
    instrument: Optional[Path],
    n_instrument: int,
    queue: Optional[Queue],
    disable_end_trigger: bool = False,
) -> list:  # noqa: D401
    """Synchronous block where sounds are sync to the heartbeat.

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
    %(instrument)s
    %(n_instrument)s
    queue : Queue
        Queue where the sequence_timings are stored. If None, this argument is
        ignored.
    %(disable_end_trigger)s

    Returns
    -------
    sequence_timings : list
        List of timings at which an R-peak occurred.
    """
    from stimuli.audio import Sound, Tone

    from .detector import Detector

    # create sound stimuli
    sound = Tone(volume, frequency=TONE_FQ, duration=0.1)
    window = tukey(sound.signal.shape[0], alpha=0.25, sym=True)
    sound._signal = np.multiply(sound.signal.T, window).T
    if instrument is not None:
        sound_instru = Sound(instrument)
        sound_instru.volume = volume

    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)

    # create peak detector
    detector = Detector(
        stream_name,
        ecg_ch_name,
        duration_buffer=4,
        peak_height_perc=peak_height_perc,
        peak_prominence=peak_prominence,
        peak_width=peak_width,
    )
    detector.prefill_buffer()

    # task loop
    trigger.signal(tdef.sync_start)
    wait(0.2, hogCPUperiod=0)

    logger.info("Starting to deliver pure tone sounds.")
    sequence_timings = _synchronous_loop(sound, sequence, detector, trigger)
    if instrument is not None:
        logger.info("Starting to deliver instrument sounds.")
        sequence_instru = [tdef.by_name[instrument.parent.name]] * n_instrument
        _synchronous_loop(sound_instru, sequence_instru, detector, trigger)

    if not disable_end_trigger:
        trigger.signal(tdef.sync_stop)

    if queue is not None:
        queue.put(sequence_timings)

    del detector

    return sequence_timings


def _synchronous_loop(sound, sequence, detector, trigger):  # noqa: D401
    """Main loop of the synchronous task."""
    # create counter/timers
    counter = 0
    # create containers for sequence timings
    sequence_timings = np.zeros(len(sequence))
    # loop
    while counter <= len(sequence) - 1:
        detector.update_loop()
        pos = detector.new_peaks()
        if pos is not None:
            # trigger
            trigger.signal(sequence[counter])
            # sound
            if sequence[counter] != 2:
                sound.play()
            logger.info("Stimuli %i/%i delivered.", counter + 1, len(sequence))
            # next
            sequence_timings[counter] = detector.timestamps_buffer[pos]
            counter += 1
            # wait for sound to be delivered before updating again
            # and give CPU time to other processes
            wait(sound.duration + 0.005, hogCPUperiod=0)

    return sequence_timings


@fill_doc
def isochronous(
    trigger,
    tdef: TriggerDef,
    sequence: ArrayLike,
    delay: float,
    volume: float,
    instrument: Optional[Path],
    n_instrument: int,
    disable_end_trigger: bool = False,
):
    """Isochronous block where sounds are delivered at a fix interval.

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
    %(instrument)s
    %(n_instrument)s
    %(disable_end_trigger)s
    """
    from stimuli.audio import Sound, Tone

    # create sound stimuli
    sound = Tone(volume, frequency=TONE_FQ, duration=0.1)
    window = tukey(sound.signal.shape[0], alpha=0.25, sym=True)
    sound._signal = np.multiply(sound.signal.T, window).T
    if instrument is not None:
        sound_instru = Sound(instrument)
        sound_instru.volume = volume

    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)
    _check_type(delay, ("numeric",), "delay")
    if delay <= 0:
        raise ValueError(
            "Argument 'delay' should be a strictly positive number. "
            f"Provided: '{delay}' seconds."
        )
    assert sound.duration < delay  # sanity-check

    wait(4, hogCPUperiod=0)  # fake buffer prefill
    # task loop
    trigger.signal(tdef.iso_start)
    wait(0.2, hogCPUperiod=0)

    logger.info("Starting to deliver pure tone sounds.")
    _isochronous_loop(sound, sequence, delay, trigger)
    if instrument is not None:
        wait(delay - sound.duration - 0.005, hogCPUperiod=0)
        logger.info("Starting to deliver instrument sounds.")
        sequence_instru = [tdef.by_name[instrument.parent.name]] * n_instrument
        _isochronous_loop(sound_instru, sequence_instru, delay, trigger)

    if not disable_end_trigger:
        trigger.signal(tdef.iso_stop)


def _isochronous_loop(sound, sequence, delay, trigger):  # noqa: D401
    """Main loop of the isochronous task."""
    # create counter/timers
    counter = 0
    # loop
    while counter <= len(sequence) - 1:
        now = ptb.GetSecs()
        trigger.signal(sequence[counter])
        # stimuli
        if sequence[counter] != 2:
            sound.play()
        logger.info("Stimuli %i/%i delivered.", counter + 1, len(sequence))
        stim_delay = ptb.GetSecs() - now

        # next
        if counter != len(sequence) - 1:
            wait_delay = delay - stim_delay
            hogCPUperiod = wait_delay - sound.duration - 0.005
            counter += 1
            wait(wait_delay, 0 if hogCPUperiod < 0 else hogCPUperiod)
        else:
            wait(sound.duration + 0.005, hogCPUperiod=0)
            break  # no more delays since it was the last stimuli


@fill_doc
def asynchronous(
    trigger,
    tdef: TriggerDef,
    sequence: ArrayLike,
    sequence_timings: ArrayLike,
    volume: float,
    instrument: Optional[Path],
    n_instrument: int,
    disable_end_trigger: bool = False,
):
    """Asynchronous block where a synchronous sequence is repeated.

    Omissions are randomized compared to the synchronous task they are
    extracted from.

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
        Array containing the timing at which the stimulus was delivered.
    %(volume)s
    %(instrument)s
    %(n_instrument)s
    %(disable_end_trigger)s
    """
    from stimuli.audio import Sound, Tone

    # Create sound stimuli
    sound = Tone(volume, frequency=TONE_FQ, duration=0.1)
    window = tukey(sound.signal.shape[0], alpha=0.25, sym=True)
    sound._signal = np.multiply(sound.signal.T, window).T
    if instrument is not None:
        sound_instru = Sound(instrument)
        sound_instru.volume = volume

    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)
    sequence_timings = _check_sequence_timings(
        sequence_timings, sequence, sound.duration
    )

    # Compute delays
    delays = np.diff(sequence_timings)  # a[i+1] - a[i]
    assert all(sound.duration < delay for delay in delays)  # sanity-check

    wait(4, hogCPUperiod=0)  # fake buffer prefill
    # Task loop
    trigger.signal(tdef.async_start)
    wait(0.2, hogCPUperiod=0)

    logger.info("Starting to deliver pure tone sounds.")
    _asynchronous_loop(sound, sequence, delays, trigger)
    if instrument is not None:
        wait(delays[-1] - sound.duration - 0.005, hogCPUperiod=0)
        logger.info("Starting to deliver instrument sounds.")
        sequence_instru = [tdef.by_name[instrument.parent.name]] * n_instrument
        delays_instru = np.random.choice(delays, size=3)
        _asynchronous_loop(
            sound_instru, sequence_instru, delays_instru, trigger
        )
    if not disable_end_trigger:
        trigger.signal(tdef.async_stop)


def _asynchronous_loop(sound, sequence, delays, trigger):  # noqa: D401
    """Main loop of the asynchronous task."""
    # create counter/timers
    counter = 0
    # loop
    while counter <= len(sequence) - 1:
        now = ptb.GetSecs()
        trigger.signal(sequence[counter])
        # stimuli
        if sequence[counter] != 2:
            sound.play()
        logger.info("Stimuli %i/%i delivered.", counter + 1, len(sequence))
        stim_delay = ptb.GetSecs() - now

        # next
        if counter != len(sequence) - 1:
            wait_delay = delays[counter] - stim_delay
            hogCPUperiod = wait_delay - sound.duration - 0.005
            counter += 1
            wait(wait_delay, 0 if hogCPUperiod < 0 else hogCPUperiod)
        else:
            wait(sound.duration + 0.005, hogCPUperiod=0)
            break  # no more delays since it was the last stimuli


@fill_doc
def baseline(
    trigger: Trigger, tdef: TriggerDef, duration: float, verbose: bool = True
):
    """
    Baseline block corresponding to a resting-state recording.

    Parameters
    ----------
    %(trigger)s
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - baseline_start
            - baseline_stop
    duration : float
        Duration of the resting-state block in seconds.
    %(task_verbose)s
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


@fill_doc
def inter_block(duration: float, verbose: bool = True):
    """
    Inter-block task-like to wait a specific duration.

    Parameters
    ----------
    duration : float
        Duration of the inter-block in seconds.
    %(task_verbose)s
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

"""Tasks functions."""

from multiprocessing import Queue
from typing import Union

import numpy as np
from numpy.typing import ArrayLike
from psychopy.clock import wait
from psychopy.sound.backend_ptb import SoundPTB as Sound
import psychtoolbox as ptb

from .detector import Detector
from .utils._checks import (_check_type, _check_tdef, _check_sequence,
                            _check_sequence_timings)
from .utils._logs import logger


def synchronous(
        trigger,
        tdef,
        sequence: ArrayLike,
        stream_name: str,
        ecg_ch_name: str,
        peak_height_perc: Union[int, float],
        peak_prominence: Union[int, float, None],
        peak_width: Union[int, float, None],
        queue: Union[Queue, None] = None,
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
    peak_prominence : float | None
        Minimum peak prominence as defined by scipy.
    peak_width : float | None
        Minimum peak width expressed in ms. Default to None.
    queue : Queue
        Queue where the sequence_timings are stored. If None, this argument is
        ignored.

    Returns
    -------
    sequence_timings : list
        List of timings at which an R-peak occured.
    """
    # Create sound stimuli
    sound = Sound(value=250, secs=0.1, stereo=True, volume=1.0, blockSize=32,
                  preBuffer=-1, hamming=True)

    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)

    # Create peak detector
    detector = Detector(
        stream_name, ecg_ch_name, duration_buffer=4,
        peak_height_perc=peak_height_perc, peak_prominence=peak_prominence,
        peak_width=peak_width)
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
            # sound
            if sequence[counter] == 1:
                sound.play(when=detector.timestamps_buffer[pos] + 0.05)
            # trigger
            wait(0.05 - ptb.GetSecs() + detector.timestamps_buffer[pos],
                 hogCPUperiod=1)
            trigger.signal(sequence[counter])
            # next
            sequence_timings.append(detector.timestamps_buffer[pos])
            counter += 1
            logger.info('Sound %i/%i delivered.', counter, len(sequence))
            # wait for sound to be delivered before updating again
            # and give CPU time to other processes
            wait(0.1, hogCPUperiod=0)

    wait(1, hogCPUperiod=0)
    trigger.signal(tdef.sync_stop)

    if queue is not None:
        queue.put(sequence_timings)

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
    # Create sound stimuli
    sound = Sound(value=250, secs=0.1, stereo=True, volume=1.0, blockSize=32,
                  preBuffer=-1, hamming=True)
    scheduling_delay = 0.2

    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)
    _check_type(delay, ('numeric', ), 'delay')
    if delay <= 0:
        raise ValueError(
            "Argument 'delay' should be a strictly positive number. "
            f"Provided: '{delay}' seconds.")
    delay -= scheduling_delay  # Remove scheduling from delay
    assert scheduling_delay < delay  # sanity-check

    # Create counter
    counter = 0

    # Task loop
    trigger.signal(tdef.iso_start)
    wait(0.2, hogCPUperiod=0)

    while counter <= len(sequence) - 1:
        if sequence[counter] == 1:
            sound.play(when=ptb.GetSecs() + scheduling_delay)
        # trigger
        wait(scheduling_delay, hogCPUperiod=1)
        trigger.signal(sequence[counter])

        # next
        wait(delay)
        counter += 1
        logger.info('Sound %i/%i delivered.', counter, len(sequence))

    wait(1, hogCPUperiod=0)
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
    # Create sound stimuli
    sound = Sound(value=250, secs=0.1, stereo=True, volume=1.0, blockSize=32,
                  preBuffer=-1, hamming=True)
    scheduling_delay = 0.2

    _check_tdef(tdef)
    sequence = _check_sequence(sequence, tdef)
    sequence_timings = _check_sequence_timings(sequence_timings, sequence,
                                               scheduling_delay)

    # Compute delays
    delays = np.diff(sequence_timings)  # a[i+1] - a[i]
    delays -= scheduling_delay  # Remove scheduling from delay
    assert all(scheduling_delay < delay for delay in delays)  # sanity-check

    # Create counter
    counter = 0

    # Task loop
    trigger.signal(tdef.async_start)
    wait(0.2, hogCPUperiod=0)

    while counter <= len(sequence) - 1:
        # stimuli
        if sequence[counter] == 1:
            sound.play(when=ptb.GetSecs() + scheduling_delay)
        # trigger
        wait(scheduling_delay, hogCPUperiod=1)
        trigger.signal(sequence[counter])

        # next
        if counter != len(sequence) - 1:
            wait(delays[counter])
            counter += 1
            logger.info('Sound %i/%i delivered.', counter, len(sequence))
        else:
            break  # no more delays since it was the last stimuli

    wait(1, hogCPUperiod=0)
    trigger.signal(tdef.async_stop)

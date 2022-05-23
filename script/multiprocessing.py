"""Test for suspending and resuming a process."""

import multiprocessing as mp
import time

import psutil
from bsl.triggers import ParallelPortTrigger

from cardio_audio_sleep.config import load_triggers
from cardio_audio_sleep.tasks import isochronous
from cardio_audio_sleep.utils import generate_sequence, search_ANT_amplifier

if __name__ == "__main__":
    trigger = ParallelPortTrigger("/dev/parport0")
    tdef = load_triggers()

    stream_name = search_ANT_amplifier()
    ecg_ch_name = "AUX7"

    sequence = generate_sequence(20, 0, 10, tdef)
    delay = 0.5

    process = mp.Process(
        target=isochronous, args=(trigger, tdef, sequence, delay, 10)
    )
    process.start()

    psutil_process = psutil.Process(process.pid)
    time.sleep(5)
    psutil_process.suspend()
    time.sleep(2)
    psutil_process.resume()

    process.join()

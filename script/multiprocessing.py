"""Test for suspending and resuming a process."""

import time
import multiprocessing as mp

from bsl.triggers import TriggerDef, ParallelPortTrigger
import psutil

from cardio_audio_sleep.tasks import isochronous
from cardio_audio_sleep.utils import search_ANT_amplifier, generate_sequence


if __name__ == '__main__':
    trigger = ParallelPortTrigger('/dev/parport0')
    directory = Path(__file__).parent.parent / 'cardio_audio_sleep' / 'config'
    tdef = TriggerDef(directory / 'triggers.ini')

    stream_name = search_ANT_amplifier()
    ecg_ch_name = 'AUX7'

    sequence = generate_sequence(20, 0, 10, tdef)
    delay = 0.5

    process = mp.Process(
        target=isochronous, args=(trigger, tdef, sequence, delay))
    process.start()

    psutil_process = psutil.Process(process.pid)
    time.sleep(5)
    psutil_process.suspend()
    time.sleep(2)
    psutil_process.resume()

    process.join()

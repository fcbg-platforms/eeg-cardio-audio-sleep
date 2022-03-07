from pathlib import Path

from bsl.triggers import TriggerDef, ParallelPortTrigger
import numpy as np

from cardio_audio_sleep.tasks import (synchronous, isochronous, asynchronous,
                                      baseline)
from cardio_audio_sleep.utils import search_ANT_amplifier, generate_sequence


#%% Triggers
trigger = ParallelPortTrigger('/dev/parport0')
directory = Path(__file__).parent.parent / 'cardio_audio_sleep' / 'config'
tdef = TriggerDef(directory / 'triggers.ini')


#%% LSL Streams
stream_name = search_ANT_amplifier()
ecg_ch_name = 'AUX7'


#%% Synchronous

# Peak detection settings
peak_height_perc = 97.5  # %
peak_width = 20  # ms
# Sequence
sequence = generate_sequence(100, 0, 10, tdef)
# Task
sequence_timings = synchronous(
    trigger, tdef, sequence, stream_name, ecg_ch_name,
    peak_height_perc, peak_width)


#%% Isochronous

# Compute inter-stimulus delay
delay = np.median(np.diff(sequence_timings))
# Sequence
sequence = generate_sequence(100, 0, 10, tdef)
# Task
isochronous(trigger, tdef, sequence, delay)


#%% Asynchronous

# Sequence
sequence = generate_sequence(100, 0, 10, tdef)
# Task
asynchronous(trigger, tdef, sequence, sequence_timings)


#%% Baseline

# Compute duration
duration = 5 * 60  # seconds
# Task
baseline(trigger, tdef, duration)

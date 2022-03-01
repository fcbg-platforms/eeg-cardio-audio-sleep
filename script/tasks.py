from pathlib import Path

from bsl.triggers import TriggerDef, ParallelPortTrigger

from cardio_audio_sleep.tasks import (synchronous, isochronous, asynchronous,
                                      baseline, generate_sequence)
from cardio_audio_sleep.utils import search_ANT_amplifier

#%% Triggers
trigger = ParallelPortTrigger('/dev/parport0')
directory = Path(__file__).parent.parent / 'cardio_audio_sleep' / 'config'
tdef = TriggerDef(directory / 'triggers.ini')

#%% LSL Streams
stream_name = search_ANT_amplifier()
ecg_ch_name = 'AUX7'

#%% Synchronous

# Peak detection settings
peak_height_perc = 97.5
peak_prominence = 700
# Sequence
sequence = generate_sequence(300, 60, 10)
# Task
synchronous(trigger, tdef, sequence, stream_name, ecg_ch_name,
            peak_height_perc, peak_prominence)

#%% Isochronous

# Compute BPM
bpm = 60
# Sequence
sequence = generate_sequence(300, 60, 10)
# Task
isochronous(trigger, tdef, sequence, bpm)

#%% Asynchronous

# Sequence
sequence = generate_sequence(300, 60, 10)
# Task
asynchronous(trigger, tdef, sequence, sequence_timings)

#%% Baseline

# Compute duration
duration = 5 * 60  # seconds
# Task
baseline(trigger, tdef, duration)

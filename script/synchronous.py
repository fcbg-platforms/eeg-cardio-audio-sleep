import time

from bsl.utils import Timer
from bsl.utils.lsl import search_lsl
from bsl.triggers.lpt import TriggerArduino2LPT

from cardio_audio_sleep import Detector, set_log_level
from cardio_audio_sleep.audio import Tone

set_log_level('DEBUG')


#%% Init
# Create sound stimuli
sound = Tone(volume=5, frequency=1000)

# Create trigger
trigger = TriggerArduino2LPT(delay=100)

# Stream settings
stream_name = search_lsl(ignore_markers=True, timeout=5)
ecg_ch_name = 'AUX7'
# Peak detection settings
peak_height_perc = 97.5
peak_prominence = 700
# Create detector
detector = Detector(
    stream_name, ecg_ch_name, duration_buffer=5,
    peak_height_perc=peak_height_perc, peak_prominence=peak_prominence)

# Create timers
timer = Timer()
audio_timer = Timer()

#%% Loop
detector.prefill_buffer()
trigger.signal(2)  # start trigger

timer.reset()
while timer.sec() <= 60:
    detector.update_loop()
    pos = detector.new_peaks()
    if pos is not None:
        audio_timer.reset()
        # compute where we are relative to the r-peak
        delay = detector.timestamps_buffer[-1] \
            - detector.timestamps_buffer[pos]
        # aim for sound at +100 ms
        while audio_timer.sec() < 0.1 - delay:
            pass
        trigger.signal(1)  # trigger when the sound is delivered
        sound.play()

trigger.signal(2)
time.sleep(0.5)
trigger.close()

import time

from psychopy import prefs
prefs.hardware['audioLib'] = 'ptb'
prefs.hardware['audioLatencyMode'] = '3'
from psychopy import parallel, sound, core
import psychtoolbox as ptb

from bsl import StreamRecorder
from bsl.utils import Timer
from bsl.utils.lsl import search_lsl

from cardio_audio_sleep import Detector, set_log_level

set_log_level('DEBUG')


#%% Stream settings
stream_name = search_lsl(ignore_markers=True, timeout=5)
ecg_ch_name = 'AUX7'

#%% Start Recorder
recorder = StreamRecorder('/home/eeg/Downloads/', fname='test',
                          fif_subdir=False, stream_name=stream_name)
recorder.start()
time.sleep(0.2)

#%% Init
mySound = sound.Sound('A', secs=0.1)
mySound.setVolume(1)

# Create trigger
port = parallel.ParallelPort(address='/dev/parport0')
port.setData(0)
core.wait(0.1)

# Peak detection settings
peak_height_perc = 97.5
peak_prominence = 700
# Create detector
detector = Detector(
    stream_name, ecg_ch_name, duration_buffer=5,
    peak_height_perc=peak_height_perc, peak_prominence=peak_prominence)

timer = Timer()

#%% Main loop
detector.prefill_buffer()
port.setData(2)
core.wait(0.1)
port.setData(0)

timer.reset()
while timer.sec() <= 60:
    detector.update_loop()
    pos = detector.new_peaks()
    if pos is not None:
        # compute where we are relative to the r-peak
        delay = detector.timestamps_buffer[-1] \
            - detector.timestamps_buffer[pos]

        now = ptb.GetSecs()
        mySound.play(when=now - delay + 0.05)

        now2 = ptb.GetSecs()
        core.wait(now2 - now - delay + 0.05)

        port.setData(1)
        core.wait(0.1)
        port.setData(0)

time.sleep(0.2)
port.setData(2)
core.wait(0.1)
port.setData(0)

#%% Stop Recorder
time.sleep(0.5)
recorder.stop()

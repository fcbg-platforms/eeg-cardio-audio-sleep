import time

from bsl import StreamRecorder
from bsl.utils.lsl import search_lsl
from psychopy.clock import Clock
from psychopy.sound.backend_ptb import SoundPTB as Sound
import psychtoolbox as ptb

from cardio_audio_sleep import Detector, set_log_level
from cardio_audio_sleep.triggers import ParallelPort

set_log_level('DEBUG')


#%% Stream settings
stream_name = search_lsl(ignore_markers=True, timeout=5)
ecg_ch_name = 'AUX7'

#%% Start Recorder
recorder = StreamRecorder('/home/eeg/Downloads/', fname='test',
                          fif_subdir=False, stream_name=stream_name)
recorder.start()
time.sleep(0.5)

#%% Init
# Create sound stimuli
sound = Sound(value='A', secs=0.1, stereo=True, volume=1.0, blockSize=32,
              preBuffer=-1, hamming=True)

# Create trigger
trigger = ParallelPort(address='/dev/parport0', delay=50)

# Peak detection settings
peak_height_perc = 97.5
peak_prominence = 700
# Create detector
detector = Detector(
    stream_name, ecg_ch_name, duration_buffer=5,
    peak_height_perc=peak_height_perc, peak_prominence=peak_prominence)

timer = Clock()
trigger_timer = Clock()

#%% Main loop
detector.prefill_buffer()
trigger.signal(2)

timer.reset()
while timer.getTime() <= 60:
    detector.update_loop()
    pos = detector.new_peaks()
    if pos is not None:
        # compute where we are relative to the r-peak
        delay = detector.timestamps_buffer[-1] \
            - detector.timestamps_buffer[pos]

        # retrieve current time and schedule sound
        time_pre_sound = ptb.GetSecs()
        sound.play(when=time_pre_sound - delay + 0.05)

        # retrieve current time and wait to deliver the trigger
        target_time = ptb.GetSecs() - time_pre_sound - delay + 0.05
        trigger_timer.reset()
        while trigger_timer.getTime() < target_time:
            pass
        trigger.signal(1)

time.sleep(0.2)
trigger.signal(2)

#%% Stop Recorder
time.sleep(0.5)
recorder.stop()

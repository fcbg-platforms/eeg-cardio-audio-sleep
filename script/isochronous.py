from bsl.utils.lsl import search_lsl
from psychopy.clock import Clock, wait
from psychopy.sound.backend_ptb import SoundPTB as Sound
import psychtoolbox as ptb

from cardio_audio_sleep import set_log_level
from cardio_audio_sleep.triggers import ParallelPort

set_log_level('DEBUG')


#%% Stream settings
stream_name = search_lsl(ignore_markers=True, timeout=5)
ecg_ch_name = 'AUX7'

#%% Init
# Create sound stimuli
sound = Sound(value='A', secs=0.1, stereo=True, volume=1.0, blockSize=32,
              preBuffer=-1, hamming=True)

# Create trigger
trigger = ParallelPort(address='/dev/parport0', delay=50)

# Sound-Sound duration
bpm = 80  # beat per minute
sleep = bpm / 60  # beat per seconds

timer = Clock()
trigger_timer = Clock()

#%% Main loop
trigger.signal(2)

timer.reset()
while timer.getTime() <= 60:
    # retrieve current time and schedule sound
    time_pre_sound = ptb.GetSecs()
    sound.play(when=time_pre_sound + 0.05)

    # retrieve current time and wait to deliver the trigger
    target_time = ptb.GetSecs() - time_pre_sound + 0.05
    trigger_timer.reset()
    while trigger_timer.getTime() < target_time:
        pass
    trigger.signal(1)

    # wait until the next cycle
    wait(sleep)

wait(0.2)
trigger.signal(2)

import math
import time

from bsl import StreamRecorder
from bsl.utils import Timer
from bsl.utils.lsl import search_lsl
from bsl.triggers.lpt import TriggerArduino2LPT
from matplotlib import pyplot as plt
import mne
import numpy as np
from scipy.signal import find_peaks

from cardio_audio_sleep import Detector, set_log_level
from cardio_audio_sleep.audio import Tone

set_log_level('DEBUG')

#%% Stream settings
stream_name = search_lsl(ignore_markers=True, timeout=5)
ecg_ch_name = 'AUX7'

#%% Recorder
recorder = StreamRecorder(
    record_dir='/home/eeg/Downloads/', fname='test', stream_name=stream_name,
    fif_subdir=False)

#%% Init
# Create sound stimuli
sound = Tone(volume=5, frequency=1000)

# Create trigger
trigger = TriggerArduino2LPT(delay=100)

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
        # aim for sound at +50 ms (computer specific tuning)
        while audio_timer.sec() < 0.030 - delay:
            pass
        trigger.signal(1)  # trigger when the sound is delivered
        sound.play()

trigger.signal(2)
time.sleep(0.5)
trigger.close()

#%% Stop Recorder
time.sleep(0.5)
recorder.stop()
time.sleep(0.5)

#%% Load file
fname = f'/home/eeg/Downloads/test-{stream_name}-raw.fif'
raw = mne.io.read_raw_fif(fname, preload=True)
raw.pick_channels(['TRIGGER', 'AUX3', 'AUX7'])
raw.set_channel_types({'AUX3': 'misc', 'AUX7': 'ecg'})
raw.rename_channels({'AUX3': 'Sound', 'AUX7': 'ECG'})

#%% Triggers
events = mne.find_events(raw, stim_channel='TRIGGER')
tmin, tmax = [elt[0] / raw.info['sfreq']
               for elt in events if elt[2] == 2]
raw.crop(tmin, tmax, include_tmax=False)

# research for events
events = mne.find_events(raw, stim_channel='TRIGGER')[1:, 0]
events -= raw.first_samp

#%% Apply notch
raw.notch_filter(np.arange(50, 251, 50), picks=['Sound', 'ECG'])

#%% Find ECG peaks
raw.filter(1., 15., picks='ECG', phase='zero-double')
data = raw.get_data(picks='ECG')[0, :]
height = np.percentile(data, 97.5)
peaks, _ = find_peaks(data, height=height)

#%% Find max after each peak on the Sound channel
delays = list()
sound = raw.get_data(picks='Sound')[0, :]
delta = math.ceil(raw.info['sfreq'] * 0.1)
for peak in peaks:
    pos = np.argmax(sound[peak:peak+delta])
    delays.append(pos / raw.info['sfreq'])

#%% Determine R-peak to event
trigger_delays = list()
triggers = raw.get_data(picks='TRIGGER')[0, :]
delta = math.ceil(raw.info['sfreq'] * 0.1)
for peak in peaks:
    pos = np.argmax(triggers[peak:peak+delta])
    trigger_delays.append(pos / raw.info['sfreq'])

#%% Plot
f, ax = plt.subplots(1, 1)
ax.plot(raw.times, data)
ax.axhline(height)
for ev in events:
    ax.axvline(raw.times[ev], color='yellow')
for peak in peaks:
    ax.axvline(raw.times[peak], color='teal', linestyle='--')

#%% Plot distributions
f, ax = plt.subplots(1, 2)
ax[0].set_title('R-peak to sound delay')
ax[0].hist(delays, bins=20)
ax[1].set_title('R-peak to event delay')
ax[1].hist(trigger_delays, bins=20)

#%% Prints
print(f'R-peak to sound (mean): {np.mean(delays):.5f} s')
print(f'R-peak to sound (std): {np.std(delays):.5f} s')
print(f'R-peak to trigger (mean): {np.mean(trigger_delays):.5f} s')
print(f'R-peak to trigger (std): {np.std(trigger_delays):.5f} s')

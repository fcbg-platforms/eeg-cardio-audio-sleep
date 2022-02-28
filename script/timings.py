import math

import mne
from matplotlib import pyplot as plt
import numpy as np
from scipy.signal import find_peaks, hilbert


#%% Load
fname = r''
raw = mne.io.read_raw_fif(fname, preload=True)
raw.rename_channels({'AUX3': 'Sound', 'AUX7': 'ECG'})
raw.pick_channels(['TRIGGER', 'Sound', 'ECG'])
raw.set_channel_types({'Sound': 'misc', 'ECG': 'ecg'})

#%% Events
events = mne.find_events(raw, stim_channel='TRIGGER')
tmin = events[0][0] / raw.info['sfreq'] if events[0][2] == 2 else None
tmax = events[-1][0] / raw.info['sfreq'] if events[-1][2] == 2 else None
raw.crop(tmin, tmax, include_tmax=True)

events = mne.find_events(raw, stim_channel='TRIGGER')
events = events[np.where(events[:, 2] != 2)]
events = np.array([ev[0] for ev in events])
events -= raw.first_samp

#%% Find peaks on ECG
raw.filter(1., 15., picks='ECG', phase='zero-double')
ecg = raw.get_data(picks='ECG')[0, :]
ecg_height = np.percentile(ecg, 97.5)
ecg_peaks, _ = find_peaks(ecg, height=ecg_height)

#%% Find sounds on Sound channel
raw.filter(1., None, picks='Sound', phase='zero-double')
sound = raw.get_data(picks='Sound')[0, :]
analytic_signal = np.abs(hilbert(sound))
analytic_signal_height = np.percentile(analytic_signal, 87)
supra_threshold_idx = np.where(analytic_signal > analytic_signal_height)[0]

sound_onsets, sound_offsets = list(), list()
for k, elt in enumerate(supra_threshold_idx):
    if k == 0:
        sound_onsets.append(elt)
        continue
    if k == len(supra_threshold_idx) - 1:
        sound_offsets.append(elt)
        continue

    if elt + 1 == supra_threshold_idx[k+1]:
        continue
    else:
        sound_offsets.append(elt)
        sound_onsets.append(supra_threshold_idx[k+1])

#%% Match trigger/sound and compute delay
d = np.repeat(sound_onsets, len(events)).reshape(
    len(sound_onsets), len(events))
d -= events
threshold = math.ceil(0.1 * raw.info['sfreq'])
id_sounds, id_triggers = np.where((-threshold < d) & (d < threshold))
assert id_sounds.shape == id_triggers.shape  # sanity-check

sound_trigger_delays = list()
for k in range(id_sounds.size):
    id_sound = id_sounds[k]
    id_trigger = id_triggers[k]
    delay = sound_onsets[id_sound] - events[id_trigger]
    sound_trigger_delays.append(delay)

#%% Match R-peak/triggers and compute delay
d = np.repeat(ecg_peaks, len(events)).reshape(
    len(ecg_peaks), len(events))
d -= events
threshold = math.ceil(0.1 * raw.info['sfreq'])
id_rpeaks, id_triggers = np.where((-threshold < d) & (d < threshold))
assert id_rpeaks.shape == id_triggers.shape  # sanity-check

rpeak_trigger_delays = list()
for k in range(id_rpeaks.size):
    id_rpeak = id_rpeaks[k]
    id_trigger = id_triggers[k]
    delay = events[id_trigger] - ecg_peaks[id_rpeak]
    rpeak_trigger_delays.append(delay)

#%% Match R-peak/sound and compute delay
d = np.repeat(ecg_peaks, len(sound_onsets)).reshape(
    len(ecg_peaks), len(sound_onsets))
d -= np.array(sound_onsets)
threshold = math.ceil(0.1 * raw.info['sfreq'])
id_rpeaks, id_sounds = np.where((-threshold < d) & (d < threshold))
assert id_rpeaks.shape == id_sounds.shape  # sanity-check

rpeak_sounds_delays = list()
for k in range(id_rpeaks.size):
    id_rpeak = id_rpeaks[k]
    id_sound= id_sounds[k]
    delay = sound_onsets[id_sound] - ecg_peaks[id_rpeak]
    rpeak_sounds_delays.append(delay)

#%% Plots
f, ax = plt.subplots(3, 1, sharex=True)

# ECG
ax[0].set_title('ECG signal')
ax[0].plot(ecg)
for peak in ecg_peaks:
    ax[0].axvline(peak, color='teal')
ax[0].axhline(ecg_height, color='lightgreen')

# Sound
ax[1].set_title('Sound')
ax[1].plot(sound)
for peak in sound_onsets:
    ax[1].axvline(peak, color='crimson')
for peak in sound_offsets:
    ax[1].axvline(peak, color='crimson', linestyle='--')

# Hilbert transformation of the sound
ax[2].set_title('Hilbert transform')
ax[2].plot(analytic_signal)
for peak in sound_onsets:
    ax[2].axvline(peak, color='crimson')
for peak in sound_offsets:
    ax[2].axvline(peak, color='crimson', linestyle='--')
ax[2].axhline(analytic_signal_height, color='lightgreen')

# Events
for ev in events:
    for a in ax:
        a.axvline(ev, color='lightblue', linestyle='--')

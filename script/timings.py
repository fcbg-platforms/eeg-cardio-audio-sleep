import math

import mne
from matplotlib import pyplot as plt
import numpy as np
from scipy.signal import find_peaks, hilbert

from cardio_audio_sleep.io import read_raw
from cardio_audio_sleep.utils import match_positions


#%% Load
fname = r''
raw = read_raw(fname, preload=True)
raw.pick_channels(['TRIGGER', 'Sound', 'ECG'])

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

assert len(sound_onsets) == len(sound_offsets)  # sanity-check
sound_durations = [offset - onset
                   for onset, offset in zip(sound_onsets, sound_offsets)]

#%% Match trigger/sound and compute delay
threshold = math.ceil(0.1 * raw.info['sfreq'])
id_sounds, id_events = match_positions(sound_onsets, events, threshold)
sound_trigger_delays = [sound_onsets[ids] - events[ide]
                        for ids, ide in zip(id_sounds, id_events)]

#%% Match R-peak/triggers and compute delay
threshold = math.ceil(0.1 * raw.info['sfreq'])
id_rpeaks, id_events = match_positions(ecg_peaks, events, threshold)
rpeak_trigger_delays = [events[ide] - ecg_peaks[idr]
                        for ide, idr in zip(id_events, id_rpeaks)]

#%% Match R-peak/sound and compute delay
threshold = math.ceil(0.1 * raw.info['sfreq'])
id_rpeaks, id_sounds = match_positions(ecg_peaks, sound_onsets, threshold)
rpeak_sounds_delays = [sound_onsets[ids] - ecg_peaks[idr]
                       for ids, idr in zip(id_sounds, id_rpeaks)]

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

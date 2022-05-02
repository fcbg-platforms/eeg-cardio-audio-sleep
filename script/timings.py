import math

import mne
import numpy as np
from matplotlib import pyplot as plt
from scipy.signal import find_peaks, hilbert

from cardio_audio_sleep.config import load_triggers
from cardio_audio_sleep.io import read_raw
from cardio_audio_sleep.utils import match_positions

#%% Sound
sound_frequency = 250.0  # in Hz
detection_threshold = 88  # in %

#%% Load
fname = r""
raw = read_raw(fname)
raw.pick_channels(["TRIGGER", "Sound", "ECG"])

#%% Triggers
tdef = load_triggers()
start = tdef.sync_start
stop = tdef.sync_stop

#%% Events
events = mne.find_events(raw, stim_channel="TRIGGER")
try:
    tmin = events[np.where(events[:, 2] == start)[0][0], 0] / raw.info["sfreq"]
    tmax = events[np.where(events[:, 2] == stop)[0][0], 0] / raw.info["sfreq"]
    raw.crop(tmin, tmax, include_tmax=True)
except IndexError:
    pass

events = mne.find_events(raw, stim_channel="TRIGGER")
events = np.array([ev[0] for ev in events if ev[2] != start and ev[2] != stop])
events -= raw.first_samp

#%% Find peaks on ECG
raw.filter(1.0, 15.0, picks="ECG", phase="zero-double")
ecg = raw.get_data(picks="ECG")[0, :]
ecg_height = np.percentile(ecg, 97.5)
ecg_peaks, _ = find_peaks(ecg, height=ecg_height)

#%% Find sounds on Sound channel
raw.filter(
    sound_frequency - 10,
    sound_frequency + 10,
    picks="Sound",
    phase="zero-double",
)
sound = raw.get_data(picks="Sound")[0, :]
analytic_signal = np.abs(hilbert(sound))
analytic_signal_height = np.percentile(analytic_signal, detection_threshold)
supra_threshold_idx = np.where(analytic_signal > analytic_signal_height)[0]

sound_onsets, sound_offsets = list(), list()
for k, elt in enumerate(supra_threshold_idx):
    if k == 0:
        sound_onsets.append(elt)
        continue
    if k == len(supra_threshold_idx) - 1:
        sound_offsets.append(elt)
        continue

    if elt + 1 == supra_threshold_idx[k + 1]:
        continue
    else:
        sound_offsets.append(elt)
        sound_onsets.append(supra_threshold_idx[k + 1])

assert len(sound_onsets) == len(sound_offsets)  # sanity-check
sound_durations = [
    offset - onset for onset, offset in zip(sound_onsets, sound_offsets)
]

#%% Match trigger/sound and compute delay
threshold = math.ceil(0.1 * raw.info["sfreq"])
id_sounds, id_events = match_positions(sound_onsets, events, threshold)
trigger_sound_delays = [
    sound_onsets[ids] - events[ide] for ids, ide in zip(id_sounds, id_events)
]

#%% Match R-peak/triggers and compute delay
threshold = math.ceil(0.1 * raw.info["sfreq"])
id_rpeaks, id_events = match_positions(ecg_peaks, events, threshold)
rpeak_trigger_delays = [
    events[ide] - ecg_peaks[idr] for ide, idr in zip(id_events, id_rpeaks)
]

#%% Match R-peak/sound and compute delay
threshold = math.ceil(0.1 * raw.info["sfreq"])
id_rpeaks, id_sounds = match_positions(ecg_peaks, sound_onsets, threshold)
rpeak_sounds_delays = [
    sound_onsets[ids] - ecg_peaks[idr]
    for ids, idr in zip(id_sounds, id_rpeaks)
]

#%% Sound/Sound delays
sound_sound_delays = np.diff(sound_onsets)

#%% Plots
f, ax = plt.subplots(3, 1, sharex=True)

# ECG
ax[0].set_title("ECG signal")
ax[0].plot(ecg)
for peak in ecg_peaks:
    ax[0].axvline(peak, color="teal")
ax[0].axhline(ecg_height, color="lightgreen")

# Sound
ax[1].set_title("Sound")
ax[1].plot(sound)
for peak in sound_onsets:
    ax[1].axvline(peak, color="crimson")
for peak in sound_offsets:
    ax[1].axvline(peak, color="crimson", linestyle="--")

# Hilbert transformation of the sound
ax[2].set_title("Hilbert transform")
ax[2].plot(analytic_signal)
for peak in sound_onsets:
    ax[2].axvline(peak, color="crimson")
for peak in sound_offsets:
    ax[2].axvline(peak, color="crimson", linestyle="--")
ax[2].axhline(analytic_signal_height, color="lightgreen")

# Events
for ev in events:
    for a in ax:
        a.axvline(ev, color="lightblue", linestyle="--")

#%% Histograms
f, ax = plt.subplots(4, 1, figsize=(5, 20))

# Trigger/Sound
ax[0].set_title("Trigger/Sound delay (samples)")
bins = np.arange(
    min(trigger_sound_delays) - 0.5, max(trigger_sound_delays) + 0.5, 1
)
ax[0].hist(trigger_sound_delays, bins=bins)

# R-peak/Trigger
ax[1].set_title("R-Peak/Trigger delay (samples)")
bins = np.arange(
    min(rpeak_trigger_delays) - 0.5, max(rpeak_trigger_delays) + 0.5, 1
)
ax[1].hist(rpeak_trigger_delays, bins=bins)

# R-Peak/Sound
ax[2].set_title("R-Peak/Sound delay (samples)")
bins = np.arange(
    min(rpeak_sounds_delays) - 0.5, max(rpeak_sounds_delays) + 0.5, 1
)
ax[2].hist(rpeak_sounds_delays, bins=bins)

# Sound/Sound
ax[3].set_title("Sound/Sound delay (samples)")
bins = np.arange(
    min(sound_sound_delays) - 0.5, max(sound_sound_delays) + 0.5, 1
)
ax[3].hist(sound_sound_delays, bins=bins)

f.tight_layout(pad=5, h_pad=5)

#%% Async
fname = r""
sequence_timings = np.load(fname)

sound_timings = (np.array(sound_onsets) - sound_onsets[0]) / raw.info["sfreq"]
sound_delays = np.diff(sound_timings)
async_delays = np.diff(sequence_timings)
f, ax = plt.subplots(1, 1)
ax.hist(sound_delays - async_delays)

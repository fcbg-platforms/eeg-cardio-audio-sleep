#%% With neurokit
import math

from matplotlib import pyplot as plt
import mne
import neurokit2 as nk
import numpy as np
from scipy.signal import butter, sosfiltfilt


# Load raw
fname = 'C:/Users/Mathieu/Documents/git/cardio-audio-sleep/data/ecg-raw.fif'
raw = mne.io.read_raw_fif(fname, preload=True)
data1 = raw.get_data()[0, :1075]
data2 = raw.get_data()[0, :1080]
data3 = raw.get_data()[0, :1090]
fs = raw.info['sfreq']

# BP filter
bp_low = 1 / (0.5 * fs)
bp_high = 15 / (0.5 * fs)
sos = butter(2, [bp_low, bp_high], btype='bandpass', output='sos')
clean1 = sosfiltfilt(sos, data1)
clean2 = sosfiltfilt(sos, data2)
clean3 = sosfiltfilt(sos, data3)

# Find peaks
method = 'kalidas2017'
peaks1 = nk.ecg.ecg_findpeaks(clean1, sampling_rate=fs, method=method)
peaks2 = nk.ecg.ecg_findpeaks(clean2, sampling_rate=fs, method=method)
peaks3 = nk.ecg.ecg_findpeaks(clean3, sampling_rate=fs, method=method)

idx = math.ceil(0.06 * fs)
peak1 = peaks1['ECG_R_Peaks'][-1]
pos1 = peak1 - idx + np.argmax(data1[peak1-idx:peak1+1])
peak2 = peaks2['ECG_R_Peaks'][-1]
pos2 = peak2 - idx + np.argmax(data2[peak2-idx:peak2+1])
peak3 = peaks3['ECG_R_Peaks'][-1]
pos3 = peak3 - idx + np.argmax(data3[peak3-idx:peak3+1])

# Plot
f, ax = plt.subplots(3, 1, sharex=True, sharey=False, figsize=(10, 5))
ax[0].plot(clean1)
ax[1].plot(clean2)
ax[2].plot(clean3)
ax[0].axvline(pos1, color='crimson', linestyle='--')
ax[1].axvline(pos2, color='crimson', linestyle='--')
ax[2].axvline(pos3, color='crimson', linestyle='--')
for peak in peaks1['ECG_R_Peaks']:
    ax[0].axvline(peak, color='teal')
for peak in peaks2['ECG_R_Peaks']:
    ax[1].axvline(peak, color='teal')
for peak in peaks3['ECG_R_Peaks']:
    ax[2].axvline(peak, color='teal')

#%% With ecgdetectors
import mne
from ecgdetectors import Detectors
from matplotlib import pyplot as plt


# Load raw
fname = 'C:/Users/Mathieu/Documents/git/cardio-audio-sleep/data/ecg-raw.fif'
raw = mne.io.read_raw_fif(fname, preload=True)
data1 = raw.get_data()[0, :1067]
data2 = raw.get_data()[0, :1075]
data3 = raw.get_data()[0, :1090]
fs = raw.info['sfreq']
detectors = Detectors(fs)

r_peaks1 = detectors.swt_detector(data1)
r_peaks2 = detectors.swt_detector(data2)
r_peaks3 = detectors.swt_detector(data3)

f, ax = plt.subplots(3, 1, sharex=True, sharey=False, figsize=(10, 5))
ax[0].plot(data1)
ax[1].plot(data2)
ax[2].plot(data3)
for peak in r_peaks1:
    ax[0].axvline(peak, color='teal')
for peak in r_peaks2:
    ax[1].axvline(peak, color='teal')
for peak in r_peaks3:
    ax[2].axvline(peak, color='teal')

import math

from ecgdetectors import Detectors
from mne import find_events
from mne.io import read_raw_fif
import numpy as np


fname = 'C:/Users/Mathieu/Downloads/test-StreamPlayer-raw.fif'
raw = read_raw_fif(fname, preload=True)
events = find_events(raw, stim_channel='TRIGGER')

# check start/stop events
assert events[0, 2] == 2 and events[-1, 2] == 2
# crop
tmin = events[0, 0] / raw.info['sfreq']
tmax = events[-1, 0] / raw.info['sfreq']
raw.crop(tmin, tmax, include_tmax=False)
# research for events
events = find_events(raw, stim_channel='TRIGGER')[:, 0]
events -= raw.first_samp

# retrieve data array
data = raw.get_data(picks='ECG')[0, :]
detectors = Detectors(raw.info['sfreq'])
r_peaks = detectors.swt_detector(data)

# retrieve r_peaks True positions
true_r_peaks = list()
for peak in r_peaks:
    idx = math.ceil(0.05 * raw.info['sfreq'])
    pos = peak - idx + np.argmax(data[peak-idx:peak])
    true_r_peaks.append(pos)

true_r_peaks = np.array(true_r_peaks)

# match r-peaks and triggers
threshold = math.ceil(0.15 * raw.info['sfreq'])
d = np.repeat(events, true_r_peaks.shape[0]).reshape(
    events.shape[0], true_r_peaks.shape[0])
d = d - true_r_peaks  # distance matrix
x, y = np.where((-threshold < d) & (d < threshold))
delays = d[x, y] * 1 / raw.info['sfreq']

# stats
print(f'Mean: {np.mean(delays):.5f} s')
print(f'STD: {np.std(delays):.5f} s')
print(f'Peak found: {events.size} / {true_r_peaks.size}')

import numpy as np
import psychtoolbox as ptb
from matplotlib import pyplot as plt
from mne.preprocessing.bads import _find_outliers

from cardio_audio_sleep import Detector
from cardio_audio_sleep.utils import search_ANT_amplifier

#%% LSL Streams
stream_name = search_ANT_amplifier()
ecg_ch_name = "AUX7"

#%% Peak detection
peak_height_perc = 97.5  # %
peak_prominence = 500
peak_width = None  # ms | None
n = 30

#%% Loop
detector = Detector(
    stream_name,
    ecg_ch_name,
    duration_buffer=4,
    peak_height_perc=peak_height_perc,
    peak_prominence=peak_prominence,
    peak_width=peak_width,
)
detector.prefill_buffer()

counter = 0
delays = list()
while counter <= n:
    detector.update_loop()
    pos = detector.new_peaks()
    if pos is not None:
        # compute where we are relative to the r-peak
        delay = ptb.GetSecs() - detector.timestamps_buffer[pos]
        delays.append(delay)
        counter += 1

#%% Remove outliers
outliers = _find_outliers(delays, threshold=3)
delays = [delay for k, delay in enumerate(delays) if k not in outliers]

#%% Convert and prepare plots
resolution = 1000 / detector.sample_rate
delays = np.array(delays) * 1000
bins = np.arange(
    min(delays) - resolution / 2, max(delays) + resolution / 2, resolution
)

#%% Plot
f, ax = plt.subplots(1, 1)
ax.set_title("Detection delays (ms)")
ax.hist(delays, bins=bins)

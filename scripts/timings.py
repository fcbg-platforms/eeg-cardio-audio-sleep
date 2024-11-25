# %% Load libraries
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from mne import Epochs, create_info, find_events
from mne.io import RawArray
from pyxdf import load_xdf
from scipy.signal import find_peaks

import cardio_audio_sleep

root = Path(cardio_audio_sleep.__file__).parent.parent / "data"


# %% Define function to load XDF files into an MNE object
def read_raw_xdf(fname: Path) -> RawArray:
    """Read an XDF file in an MNE raw object."""
    stream = load_xdf(root / fname)[0][0]
    ch_names = [
        ch["label"][0] for ch in stream["info"]["desc"][0]["channels"][0]["channel"]
    ]
    info = create_info(ch_names, 1024, "eeg")
    raw = RawArray(stream["time_series"].T, info)
    raw.pick(("TRIGGER", "AUX7", "AUX8"))
    raw.set_channel_types({"TRIGGER": "stim", "AUX7": "ecg", "AUX8": "misc"})
    raw.rename_channels({"AUX7": "ECG", "AUX8": "Sound"})
    return raw


# %% Isochronous
fname = root / "isochronous.xdf"
raw = read_raw_xdf(fname)
events = find_events(raw)
events = events[events[:, 2] == 1]  # only keep the sound events
epochs = Epochs(raw, events, tmin=-0.05, tmax=0.25, picks="misc")
epochs.plot(picks="Sound", n_epochs=1, events=events, scalings=dict(misc=4e5))

# the target delay was 0.5 seconds
delays_sample = np.diff(events[:, 0])
delays_ms = delays_sample * 1000 / raw.info["sfreq"]
f, ax = plt.subplots(1, 2, layout="constrained")
f.suptitle("Task: isochronous - target: 500 ms")
ax[0].hist(
    delays_sample,
    bins=np.arange(np.min(delays_sample) - 0.5, np.max(delays_sample) + 1.5, 1),
    edgecolor="black",
)
ax[0].set_title("Distribution of delays in samples")
ax[0].set_xlabel("Samples")
ax[0].set_xticks(np.arange(np.min(delays_sample), np.max(delays_sample) + 1, 1))
ax[1].hist(
    delays_ms,
    bins=np.arange(
        np.min(delays_ms) - 0.5 * 1000 / raw.info["sfreq"],
        np.max(delays_ms) + 1.5 * 1000 / raw.info["sfreq"],
        1000 / raw.info["sfreq"],
    ),
    edgecolor="black",
)
ax[1].set_title("Distribution of delays in ms")
ax[1].set_xlabel("ms")
ax[1].set_xticks(
    np.arange(
        np.min(delays_ms),
        np.max(delays_ms) + 1000 / raw.info["sfreq"],
        1000 / raw.info["sfreq"],
    )
)

# %% Asynchronous
fname = root / "asynchronous.xdf"
raw = read_raw_xdf(fname)
events = find_events(raw)
events = events[events[:, 2] == 1]  # only keep the sound events
epochs = Epochs(raw, events, tmin=-0.05, tmax=0.25, picks="misc")
epochs.plot(picks="Sound", n_epochs=1, events=events, scalings=dict(misc=4e5))

# the target delay was 0.5 to 0.8 seconds (uniformly distributed)
delays_sample = np.diff(events[:, 0])
delays_ms = delays_sample * 1000 / raw.info["sfreq"]
f, ax = plt.subplots(1, 2, layout="constrained")
f.suptitle("Task: asynchronous - target: 500-800 ms")
ax[0].hist(
    delays_sample,
    bins=np.arange(np.min(delays_sample) - 10, np.max(delays_sample) + 11, 20),
    edgecolor="black",
)
ax[0].set_title("Distribution of delays in samples")
ax[0].set_xlabel("Samples")
ax[0].set_xticks(np.arange(np.min(delays_sample), np.max(delays_sample) + 1, 100))
ax[1].hist(
    delays_ms,
    bins=np.arange(
        np.min(delays_ms) - 10 * 1000 / raw.info["sfreq"],
        np.max(delays_ms) + 11 * 1000 / raw.info["sfreq"],
        20 * 1000 / raw.info["sfreq"],
    ),
    edgecolor="black",
)
ax[1].set_title("Distribution of delays in ms")
ax[1].set_xlabel("ms")
ax[1].set_xticks(
    np.arange(
        np.min(delays_ms),
        np.max(delays_ms) + 1000 / raw.info["sfreq"],
        100 * 1000 / raw.info["sfreq"],
    )
)

# %% Synchronous
fname = root / "synchronous.xdf"
raw = read_raw_xdf(fname)
events = find_events(raw)
events = events[events[:, 2] == 1]  # only keep the sound events
epochs = Epochs(raw, events, tmin=-0.05, tmax=0.25, picks="misc")
epochs.plot(picks="Sound", n_epochs=1, events=events, scalings=dict(misc=4e5))

# filter the signal with the same filters as the detector
raw.notch_filter(50, picks="ECG", method="iir", phase="forward")
raw.notch_filter(100, picks="ECG", method="iir", phase="forward")
raw.crop(5, None)  # time for the filter without initial state to settle
data = raw.get_data(picks="ECG").squeeze()

# detect r-peaks
peaks = find_peaks(data, prominence=500, distance=0.8 * raw.info["sfreq"])[0]
events[:, 0] -= raw.first_samp
f, ax = plt.subplots(1, 1, layout="constrained")
ax.plot(raw.times, data, color="blue")
for peak in peaks:
    ax.axvline(raw.times[peak], color="red", linestyle="--")
for event in events:
    ax.axvline(raw.times[event[0]], color="black", linestyle="--")


# plot the distribution of delays
def match_positions(x, y, threshold: int):
    """Match position between X and Y."""
    x = np.array(x)
    y = np.array(y)
    d = np.repeat(x, y.shape[0]).reshape(x.shape[0], y.shape[0])
    d -= y
    idx, idy = np.where((-threshold < d) & (d < threshold))
    assert idx.shape == idy.shape  # sanity-check
    return idx, idy


idx_peaks, idx_events = match_positions(peaks, events[:, 0], 0.5 * raw.info["sfreq"])
peaks = peaks[idx_peaks]
events = events[idx_events, 0]
delays_sample = events - peaks
delays_ms = delays_sample * 1000 / raw.info["sfreq"]
f, ax = plt.subplots(1, 2, layout="constrained")
f.suptitle("Task: synchronous respiration - target: 50 ms post peak")
ax[0].hist(
    delays_sample,
    bins=np.arange(np.min(delays_sample) - 0.5, np.max(delays_sample) + 1.5, 1),
    edgecolor="black",
)
ax[0].set_title("Distribution of delays in samples")
ax[0].set_xticks(np.arange(np.min(delays_sample), np.max(delays_sample) + 1, 60))
ax[0].set_xlabel("Samples")
ax[1].hist(
    delays_ms,
    bins=np.arange(
        np.min(delays_ms) - 0.5 * 1000 / raw.info["sfreq"],
        np.max(delays_ms) + 1.5 * 1000 / raw.info["sfreq"],
        1000 / raw.info["sfreq"],
    ),
    edgecolor="black",
)
ax[1].set_title("Distribution of delays in ms")
ax[1].set_xticks(
    np.arange(
        np.min(delays_ms),
        np.max(delays_ms) + 1000 / raw.info["sfreq"],
        1000 / raw.info["sfreq"],
    )
)
ax[1].set_xlabel("ms")

import mne
import numpy as np
from mne.io import BaseRaw

from ..config import load_triggers


def map_aux(
    raw: BaseRaw,
    *,
    sound: str = "AUX3",
    ecg: str = "AUX7",
    veog: str = "EOG",
    heog: str = "AUX8",
    emg: str = "AUX9",
    respiration: str = "AUX10",
) -> BaseRaw:
    """
    Map the AUX channels correctly (in-place).

    Parameters
    ----------
    raw : Raw
    sound : str
        Name of the sound auxiliary channel.
    ecg : str
        Name of the ECG auxiliary channel.
    veog : str
        Name of the vertical EOG channel (inc. on the cap layout).
    heog : str
        Name of the horizontal EOG auxiliary channel.
    emg : str
        Name of the EMG auxiliary channel.
    respiration : str
        Name of the respiration belt auxiliary channel.

    Returns
    -------
    raw : Raw
    """
    names_mapping = dict()
    types_mapping = dict()
    if sound in raw.ch_names:
        names_mapping[sound] = "Sound"
        types_mapping["Sound"] = "misc"
    if ecg in raw.ch_names:
        names_mapping[ecg] = "ECG"
        types_mapping["ECG"] = "ecg"
    if veog in raw.ch_names:
        names_mapping[veog] = "vEOG"
        types_mapping["vEOG"] = "eog"
    if heog in raw.ch_names:
        names_mapping[heog] = "hEOG"
        types_mapping["hEOG"] = "eog"
    if emg in raw.ch_names:
        names_mapping[emg] = "EMG"
        types_mapping["EMG"] = "emg"
    if respiration in raw.ch_names:
        names_mapping[respiration] = "Respiration"
        types_mapping["Respiration"] = "misc"

    raw.rename_channels(names_mapping)
    raw.set_channel_types(types_mapping)
    return raw


def add_annotations_from_events(raw: BaseRaw) -> BaseRaw:
    """
    Add annotations from events.

    Parameters
    ----------
    raw : Raw

    Returns
    -------
    raw : Raw
    """
    events = mne.find_events(raw, stim_channel="TRIGGER")
    tdef = load_triggers()

    # Block start/stop
    blocks = {
        "Synchronous": (tdef.sync_start, tdef.sync_stop),
        "Isochronous": (tdef.iso_start, tdef.iso_stop),
        "Asynchornous": (tdef.async_start, tdef.async_stop),
        "Baseline": (tdef.baseline_start, tdef.baseline_stop),
    }
    for block, (tdef_start, tdef_stop) in blocks.items():
        starts = np.sort(np.where(events[:, 2] == tdef_start)[0])
        stops = np.sort(np.where(events[:, 2] == tdef_stop)[0])
        if starts.shape != stops.shape:
            continue  # TODO: Consider mismatch
        onsets = [events[start, 0] / raw.info["sfreq"] for start in starts]
        durations = [
            (events[stop, 0] - events[start, 0]) / raw.info["sfreq"]
            for start, stop in zip(starts, stops)
        ]
        annotations = mne.Annotations(onsets, durations, block)
        raw.set_annotations(raw.annotations + annotations)

    # Pause/Resume
    pause = np.sort(np.where(events[:, 2] == tdef.pause)[0])
    resume = np.sort(np.where(events[:, 2] == tdef.resume)[0])
    if pause.shape == resume.shape:  # TODO: Consider mismatch
        onsets = [events[start, 0] / raw.info["sfreq"] for start in pause]
        durations = [
            (events[stop, 0] - events[start, 0]) / raw.info["sfreq"]
            for start, stop in zip(pause, resume)
        ]
        annotations = mne.Annotations(onsets, durations, "BAD_Pause")
        raw.set_annotations(raw.annotations + annotations)

    # Sounds/Omissions
    duration = 0.1  # TODO: to be changed when sounds are better defined.
    for name, event in (("Sound", tdef.sound), ("Omission", tdef.omission)):
        stim = np.where(events[:, 2] == event)[0]
        onsets = [events[start, 0] / raw.info["sfreq"] for start in stim]
        annotations = mne.Annotations(onsets, duration, name)
        raw.set_annotations(raw.annotations + annotations)

    return raw

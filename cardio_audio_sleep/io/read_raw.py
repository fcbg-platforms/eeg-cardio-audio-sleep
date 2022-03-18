import mne
import numpy as np

from ..config import load_triggers


def read_raw(fname):
    """
    Read raw FIF file and set channels.

    Parameters
    ----------
    fname : file-like
        Path to the -raw.fif file to load.

    Returns
    -------
    raw : Raw
        MNE raw instance.
    """
    raw = mne.io.read_raw_fif(fname, preload=True)

    # AUX channels
    names_mapping = dict()
    types_mapping = dict()
    if 'AUX3' in raw.ch_names:
        names_mapping['AUX3'] = 'Sound'
        types_mapping['Sound'] = 'misc'
    if 'AUX7' in raw.ch_names:
        names_mapping['AUX7'] = 'ECG'
        types_mapping['ECG'] = 'ecg'

    raw.rename_channels(names_mapping)
    raw.set_channel_types(types_mapping)

    # Old eego LSL plugin has upper case channel names
    mapping = {
        "FP1": "Fp1",
        "FPZ": "Fpz",
        "FP2": "Fp2",
        "FZ": "Fz",
        "CZ": "Cz",
        "PZ": "Pz",
        "POZ": "POz",
        "FCZ": "FCz",
        "OZ": "Oz",
        "FPz": "Fpz",
    }
    for key, value in mapping.items():
        try:
            mne.rename_channels(raw.info, {key: value})
        except Exception:
            pass

    # Set annotations
    events = mne.find_events(raw, stim_channel='TRIGGER')
    tdef = load_triggers()
    blocks = {
        'Synchronous': (tdef.sync_start, tdef.sync_stop),
        'Isochronous': (tdef.iso_start, tdef.iso_stop),
        'Asynchornous': (tdef.async_start, tdef.async_stop),
        'Baseline': (tdef.baseline_start, tdef.baseline_stop),
        }

    # Block start/stop
    for block, (tdef_start, tdef_stop) in blocks.items():
        starts = np.sort(np.where(events[:, 2] == tdef_start)[0])
        stops = np.sort(np.where(events[:, 2] == tdef_stop)[0])
        if starts.shape != stops.shape:
            continue  # TODO: Consider mismatch
        onsets = [events[start, 0] / raw.info['sfreq']
                  for start in starts]
        durations = [(events[stop, 0] - events[start, 0]) / raw.info['sfreq']
                     for start, stop in zip(starts, stops)]
        annotations = mne.Annotations(onsets, durations, block)
        raw.set_annotations(raw.annotations + annotations)

    # Pause/Resume
    pause = np.sort(np.where(events[:, 2] == tdef.pause)[0])
    resume = np.sort(np.where(events[:, 2] == tdef.resume)[0])
    if pause.shape == resume.shape:  # TODO: Consider mismatch
        onsets = [events[start, 0] / raw.info['sfreq']
                  for start in pause]
        durations = [(events[stop, 0] - events[start, 0]) / raw.info['sfreq']
                     for start, stop in zip(pause, resume)]
        annotations = mne.Annotations(onsets, durations, 'Pause')
        raw.set_annotations(raw.annotations + annotations)

    # Sounds/Omissions
    duration = 0.1  # TODO: to be changed when sounds are better defined.
    sounds = np.where(events[:, 2] == tdef.sound)[0]
    onsets = [events[start, 0] / raw.info['sfreq'] for start in sounds]
    annotations = mne.Annotations(onsets, duration, 'Sound')
    raw.set_annotations(raw.annotations + annotations)
    omissions = np.where(events[:, 2] == tdef.omission)[0]
    onsets = [events[start, 0] / raw.info['sfreq'] for start in omissions]
    annotations = mne.Annotations(onsets, duration, 'Omission')
    raw.set_annotations(raw.annotations + annotations)

    return raw

import mne


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
    types_mapping =dict()
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

    return raw

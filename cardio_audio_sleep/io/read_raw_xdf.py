import numpy as np
from mne import Annotations, create_info, rename_channels
from mne.io import RawArray
from mne.io.pick import _DATA_CH_TYPES_ORDER_DEFAULT
from pyxdf import load_xdf

from .utils import add_annotations_from_events, map_aux


def read_raw_xdf(fname):
    """
    Read raw XDF files saved with the LabRecorder.

    Parameters
    ----------
    fname : file-like
        Path to the -raw.fif file to load.

    Returns
    -------
    raw : Raw
        MNE raw instance.
    """
    streams, _ = load_xdf(fname)
    assert len(streams) in (1, 2)
    _, eeg_stream = find_streams(streams, "eego")[0]
    try:
        _, instrument_stream = find_streams(streams, "instruments")[0]
    except IndexError:
        instrument_stream = None
    del streams
    # retrieve information
    ch_names, ch_types, units = _get_eeg_ch_info(eeg_stream)
    sfreq = int(eeg_stream["info"]["nominal_srate"][0])
    data = eeg_stream["time_series"].T
    # create MNE raw
    info = create_info(ch_names, sfreq, ch_types)
    raw = RawArray(data, info, first_samp=0)
    # AUX channels
    raw = map_aux(raw)
    # rename channels to standard 10/20 convention
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
            rename_channels(raw.info, {key: value})
        except Exception:
            pass

    # scaling
    raw.apply_function(
        lambda x: x*1e-6, picks=["eeg", "eog", "ecg", "misc"], channel_wise=False
    )
    # annotations
    raw = add_annotations_from_events(raw)
    if instrument_stream is not None:
        onsets = list()
        durations = list()
        names = list()
        for ts, name in zip(
            instrument_stream["time_stamps"],
            instrument_stream["time_series"],
            strict=True,
        ):
            idx = np.searchsorted(eeg_stream["time_stamps"], ts)
            onsets.append(raw.times[idx])
            durations.append(5)  # fix duration for now
            names.append(name[0])
        annotations = Annotations(onsets, durations, names)
        raw.set_annotations(raw.annotations + annotations)

    return raw


def find_streams(
    streams: list[dict],
    stream_name: str,
) -> list[tuple[int, dict]]:
    """Find the stream including 'stream_name' in the name attribute.

    Parameters
    ----------
    streams : list of dict
        List of streams loaded by pyxdf.
    stream_name : str
        Substring that has to be present in the name attribute.

    Returns
    -------
    list of tuples : (k: int, stream: dict)
        k is the idx of stream in streams.
        stream is the stream that contains stream_name in its name.
    """
    return [
        (k, stream)
        for k, stream in enumerate(streams)
        if stream_name in stream["info"]["name"][0]
    ]


def _get_eeg_ch_info(stream):
    """Extract the info for each eeg channels (label, type and unit)."""
    ch_names, ch_types, units = [], [], []

    # get channels labels, types and units
    for ch in stream["info"]["desc"][0]["channels"][0]["channel"]:
        ch_type = ch["type"][0].lower()
        if ch_type not in _DATA_CH_TYPES_ORDER_DEFAULT:
            # to be changed to a dict if to many entries exist.
            ch_type = "stim" if ch_type == "markers" else ch_type
            ch_type = "misc" if ch_type == "aux" else ch_type

        ch_names.append(ch["label"][0])
        ch_types.append(ch_type)
        units.append(ch["unit"][0])

    return ch_names, ch_types, units

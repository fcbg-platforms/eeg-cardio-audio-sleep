from pathlib import Path

import numpy as np

from ._checks import _check_type, _check_value


def pick_instrument_sound(
    instrument_sync: str,
    instrument_iso: str,
    instrument_async: str,
    n: int,
):
    """Pick N instrument sound from the instrument category.

    Parameters
    ----------
    instrument_sync : str
        Instrument category for the synchronous condition.
    instrument_iso : str
        Instrument category for the isochronous condition.
    instrument_async : str
        Instrument category for the asynchronous condition.
    n : int
        Number of sounds to pick for each condition.

    Returns
    -------
    instrument_files : Path
        Path to the .wav sound picked.
    """
    _check_type(instrument_sync, (str,), "instrument_sync")
    _check_type(instrument_iso, (str,), "instrument_sync")
    _check_type(instrument_async, (str,), "instrument_sync")
    _check_type(n, ("int",), "n")
    assert 0 < n

    directory = Path(__file__).parent.parent / "audio"
    assert directory.exists() and directory.is_dir()  # sanity-check
    instrument_categories = tuple(
        [elt.name for elt in directory.iterdir() if elt.is_dir()]
    )
    _check_value(instrument_sync, instrument_categories, "instrument_sync")
    _check_value(instrument_iso, instrument_categories, "instrument_iso")
    _check_value(instrument_async, instrument_categories, "instrument_async")

    instruments = dict(
        synchronous=instrument_sync,
        isochronous=instrument_iso,
        asynchronous=instrument_async,
    )
    instrument_files = dict()
    for condition, instrument in instruments.items():
        files = [
            elt
            for elt in (directory / instrument).iterdir()
            if elt.suffix == ".wav"
        ]
        if len(files) < n:
            raise RuntimeError("Not enough sound files to pick from.")
        instrument_files[condition] = np.random.choice(files, 3)

    return instrument_files

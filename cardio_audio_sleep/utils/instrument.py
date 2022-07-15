from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from ._checks import _check_type, _check_value


def load_instrument_categories() -> List[str]:
    """Load the available instrument categories."""
    directory = Path(__file__).parent.parent / "audio"
    assert directory.exists() and directory.is_dir()  # sanity-check
    instrument_categories = tuple(
        [elt.name for elt in directory.iterdir() if elt.is_dir()]
    )
    assert len(instrument_categories) != 0  # sanity-check
    return sorted(instrument_categories)


def pick_instrument_sound(
    instrument_sync: Optional[str],
    instrument_iso: Optional[str],
    instrument_async: Optional[str],
    exclude: Union[List[Path], Tuple[Path, ...]],
    n: int,
) -> Dict[str, Path]:
    """Pick N instrument sound from the instrument category.

    Parameters
    ----------
    instrument_sync : str | None
        Instrument category for the synchronous condition.
    instrument_iso : str | None
        Instrument category for the isochronous condition.
    instrument_async : str | None
        Instrument category for the asynchronous condition.
    exclude : list of Path | tuple of Path
        List of instrument files to exclude.
    n : int
        Number of sounds to pick for each condition.

    Returns
    -------
    instrument_files : dict
        Dictionary with the path to the .wav sound picked for each condition.
    """
    _check_type(instrument_sync, (str, None), "instrument_sync")
    _check_type(instrument_iso, (str, None), "instrument_sync")
    _check_type(instrument_async, (str, None), "instrument_sync")
    _check_type(exclude, (list, tuple), "exclude")
    for elt in exclude:
        _check_type(elt, (Path,))
    _check_type(n, ("int",), "n")
    assert 0 < n

    directory = Path(__file__).parent.parent / "audio"
    assert directory.exists() and directory.is_dir()  # sanity-check
    instrument_categories = load_instrument_categories()
    if instrument_sync is not None:
        _check_value(instrument_sync, instrument_categories, "instrument_sync")
    if instrument_iso is not None:
        _check_value(instrument_iso, instrument_categories, "instrument_iso")
    if instrument_async is not None:
        _check_value(
            instrument_async, instrument_categories, "instrument_async"
        )

    instruments = dict(
        synchronous=instrument_sync,
        isochronous=instrument_iso,
        asynchronous=instrument_async,
    )
    instrument_files = dict()
    for condition, instrument in instruments.items():
        if instrument is None:
            instrument_files[condition] = None
            continue
        files = [
            elt
            for elt in (directory / instrument).iterdir()
            if elt.suffix == ".wav" and elt not in exclude
        ]
        if len(files) < n:
            raise RuntimeError("Not enough sound files to pick from.")
        instrument_files[condition] = np.random.choice(files, n, replace=False)

    return instrument_files

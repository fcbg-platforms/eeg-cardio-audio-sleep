import random
from pathlib import Path

from ._checks import _check_type, _check_value


def pick_instrument_sound(instrument: str):
    """Pick an instrument sound from the instrument category.

    Parameters
    ----------
    instrument : str
        Instrument category.

    Returns
    -------
    instrument_sound : Path
        Path to the .wav sound picked.
    """
    _check_type(instrument, (str,), "instrument")
    directory = Path(__file__).parent.parent / "audio"
    assert directory.exists() and directory.is_dir()  # sanity-check
    instrument_categories = tuple(
        [elt.name for elt in directory.iterdir() if elt.is_dir()]
    )
    _check_value(instrument, instrument_categories, "instrument")
    instrument_sounds = [
        elt
        for elt in (directory / instrument).iterdir()
        if elt.suffix == ".wav"
    ]
    return random.choice(instrument_sounds)

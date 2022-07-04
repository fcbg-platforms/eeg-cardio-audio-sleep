import random
from pathlib import Path
from typing import List, Tuple, Union

from ._checks import _check_type, _check_value
from ._logs import logger


def pick_instrument_sound(
    instrument: str,
    exclude: Union[List[str], Tuple[str, ...]] = [],
):
    """Pick an instrument sound from the instrument category.

    Parameters
    ----------
    instrument : str
        Instrument category.
    exclude : list of str | tuple of str
        Instrument file name to ignore.

    Returns
    -------
    instrument_sound : Path
        Path to the .wav sound picked.
    """
    _check_type(instrument, (str,), "instrument")
    _check_type(exclude, (list, tuple), "exclude")
    for elt in exclude:
        _check_type(elt, (str,))
    directory = Path(__file__).parent.parent / "audio"
    assert directory.exists() and directory.is_dir()  # sanity-check
    instrument_categories = tuple(
        [elt.name for elt in directory.iterdir() if elt.is_dir()]
    )
    _check_value(instrument, instrument_categories, "instrument")
    instrument_sounds = [
        elt
        for elt in (directory / instrument).iterdir()
        if elt.suffix == ".wav" and elt.name not in exclude
    ]
    if len(instrument_sounds) == 0:
        logger.error(
            "No more instrument sounds to choose from! "
            "Choosing an instrument sound from the entire library."
        )
        instrument_sounds = [
            elt
            for elt in (directory / instrument).iterdir()
            if elt.suffix == ".wav"
        ]
    return random.choice(instrument_sounds)

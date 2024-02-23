from pathlib import Path

import numpy as np

from ._checks import check_type, check_value, ensure_int


def load_instrument_categories() -> list[str]:
    """Load the available instrument categories."""
    directory = Path(__file__).parent.parent / "audio"
    assert directory.exists() and directory.is_dir()  # sanity-check
    instrument_categories = tuple(
        [elt.name for elt in directory.iterdir() if elt.is_dir()]
    )
    assert len(instrument_categories) != 0  # sanity-check
    return sorted(instrument_categories)


def load_instrument_images() -> dict[str, str]:
    """Load the available instrument categories and their images."""
    instrument_categories = load_instrument_categories()
    directory = Path(__file__).parent.parent / "visuals"
    assert directory.exists() and directory.is_dir()  # sanity-check
    instrument_categories_visuals = tuple(
        [elt.name for elt in directory.iterdir() if elt.is_dir()]
    )
    assert instrument_categories == sorted(instrument_categories_visuals)
    images = dict()
    for instrument in instrument_categories:
        files = [
            elt
            for elt in (directory / instrument).iterdir()
            if elt.is_file() and not elt.name.startswith(".")
        ]
        assert len(files) == 1
        images[instrument] = str(files[0])
    return images


def pick_instrument_sound(
    instrument_sync: str | None,
    instrument_iso: str | None,
    instrument_async: str | None,
    exclude: list[Path] | tuple[Path, ...],
    n: int,
    seed: int | None = None,
) -> dict[str, Path]:
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
    seed : int | None
        The random seed to use. If None, the random seed is not set

    Returns
    -------
    instrument_files : dict
        Dictionary with the path to the .wav sound picked for each condition.
    """
    check_type(instrument_sync, (str, None), "instrument_sync")
    check_type(instrument_iso, (str, None), "instrument_sync")
    check_type(instrument_async, (str, None), "instrument_sync")
    check_type(exclude, (list, tuple), "exclude")
    for elt in exclude:
        check_type(elt, (Path,))
    n = ensure_int(n, "n")
    assert 0 < n
    check_type(seed, ("int-like", None), "seed")
    if seed is not None:
        np.random.seed(seed)

    directory = Path(__file__).parent.parent / "audio"
    assert directory.exists() and directory.is_dir()  # sanity-check
    instrument_categories = load_instrument_categories()
    if instrument_sync is not None:
        check_value(instrument_sync, instrument_categories, "instrument_sync")
    if instrument_iso is not None:
        check_value(instrument_iso, instrument_categories, "instrument_iso")
    if instrument_async is not None:
        check_value(instrument_async, instrument_categories, "instrument_async")

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

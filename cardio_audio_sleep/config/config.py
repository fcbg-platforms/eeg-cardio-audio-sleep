from configparser import ConfigParser
from pathlib import Path
from typing import Tuple

from bsl.triggers import TriggerDef

from ..utils._checks import _check_type, _check_value


def load_triggers() -> TriggerDef:
    """Load triggers from triggers.ini into a TriggerDef instance.

    Returns
    -------
    tdef : TriggerDef
        Trigger definitiopn containing: sound, omission, sync_start, sync_stop,
        iso_start, iso_stop, async_start, async_stop, baseline_start and
        baseline_stop, recollection, pause, resume and the instruments.
    """
    directory = Path(__file__).parent
    tdef = TriggerDef(directory / "triggers.ini")

    keys = (
        "sound",
        "omission",
        "sync_start",
        "sync_stop",
        "iso_start",
        "iso_stop",
        "async_start",
        "async_stop",
        "baseline_start",
        "baseline_stop",
        "recollection",
        "pause",
        "resume",
    )
    for key in keys:
        if not hasattr(tdef, key):
            raise ValueError(
                f"Key '{key}' is missing from trigger definition."
            )

    directory = Path(__file__).parent.parent / "audio"
    assert directory.exists() and directory.is_dir()  # sanity-check
    instrument_categories = tuple(
        [elt.name for elt in directory.iterdir() if elt.is_dir()]
    )
    for instrument in instrument_categories:
        if not hasattr(tdef, instrument):
            raise ValueError(
                f"Key '{instrument}' is missing from trigger definition."
            )

    return tdef


def load_config(fname: str, dev: bool = False) -> Tuple[dict, str]:
    """Load config from config.ini.

    Parameters
    ----------
    fname : str
        Name of the config file to load (with the externsion included).
    dev : bool
        If True, the config-dev.ini file is used instead.

    Returns
    -------
    config : dict
    """
    _check_type(fname, (str,), "fname")
    _check_type(dev, (bool,), "dev")

    directory = Path(__file__).parent
    config = ConfigParser(inline_comment_prefixes=("#", ";"))
    config.optionxform = str
    stem, ext = fname.split(".")
    assert ext == "ini"
    fname = stem + "-dev." + ext if dev else fname
    config.read(str(directory / fname))

    keys = (
        "trigger",
        "block",
        "baseline",
        "synchronous",
        "isochronous",
        "asynchronous",
    )
    for key in keys:
        if not config.has_section(key):
            raise ValueError(f"Key '{key}' is missing from configuration.")

    # retrieve trigger type
    trigger = config["trigger"]["type"]
    _check_value(trigger, ("lpt", "mock"), "trigger")

    # convert all to int
    block = {key: int(value) for key, value in dict(config["block"]).items()}
    baseline = {
        key: int(value) for key, value in dict(config["baseline"]).items()
    }
    synchronous = {
        key: int(eval(value))
        for key, value in dict(config["synchronous"]).items()
    }
    isochronous = {
        key: int(eval(value))
        for key, value in dict(config["isochronous"]).items()
    }
    asynchronous = {
        key: int(eval(value))
        for key, value in dict(config["asynchronous"]).items()
    }

    # check keys
    assert "inter_block" in block
    assert "duration" in baseline
    assert all(
        key in synchronous
        for key in (
            "n_stimuli",
            "n_omissions",
            "edge_perc",
            "instrument",
            "n_instrument",
        )
    )
    assert all(
        key in isochronous
        for key in (
            "n_stimuli",
            "n_omissions",
            "edge_perc",
            "instrument",
            "n_instrument",
        )
    )
    assert all(
        key in asynchronous
        for key in (
            "n_stimuli",
            "n_omissions",
            "edge_perc",
            "instrument",
            "n_instrument",
        )
    )

    # overwrite edge_perc with float
    synchronous["edge_perc"] = config["synchronous"].getfloat("edge_perc")
    isochronous["edge_perc"] = config["isochronous"].getfloat("edge_perc")
    asynchronous["edge_perc"] = config["asynchronous"].getfloat("edge_perc")

    # overwrite instrument with boolean
    synchronous["instrument"] = bool(synchronous["instrument"])
    isochronous["instrument"] = bool(isochronous["instrument"])
    asynchronous["instrument"] = bool(asynchronous["instrument"])

    # check that the values make sense
    assert 0 < synchronous["n_stimuli"]
    assert 0 < isochronous["n_stimuli"]
    assert 0 < asynchronous["n_stimuli"]
    for key in ("n_omissions", "n_instrument"):
        assert 0 <= synchronous[key]
        assert 0 <= isochronous[key]
        assert 0 <= asynchronous[key]
    assert 0 <= synchronous["edge_perc"] <= 100
    assert 0 <= isochronous["edge_perc"] <= 100
    assert 0 <= asynchronous["edge_perc"] <= 100

    config = {
        "block": block,
        "baseline": baseline,
        "synchronous": synchronous,
        "isochronous": isochronous,
        "asynchronous": asynchronous,
    }

    return config, trigger

import numpy as np
import pytest

from resp_audio_sleep.tasks._config import N_DEVIANT, N_TARGET
from resp_audio_sleep.tasks._utils import (
    _check_triggers,
    _ensure_valid_frequencies,
    generate_sequence,
)


def test_check_triggers():
    """Test trigger dictionary validation."""
    _check_triggers(triggers={"target/1000.0": 1, "deviant/1000.0": 2})
    _check_triggers(triggers={"target/1000.5": 1, "deviant/1000.4234": 2})
    with pytest.raises(TypeError, match="'trigger-key' must be an instance of str"):
        _check_triggers(triggers={1: 2})
    with pytest.raises(ValueError, match="The trigger names must be in the format"):
        _check_triggers(triggers={"targe/1000": 1, "deviant/1000": 2})
    with pytest.raises(ValueError, match="The trigger names must be in the format"):
        _check_triggers(triggers={"target/1000.0.1": 1, "deviant/1000": 2})
    with pytest.raises(ValueError, match="The trigger names must be in the format"):
        _check_triggers(triggers={"target/blabla": 1, "deviant/1000": 2})


def test_ensure_valid_frequencies():
    """Test validation of frequencies."""
    triggers = {"target/1000.0": 1, "deviant/2000.0": 2}
    frequencies = _ensure_valid_frequencies(
        {"target": 1000, "deviant": 2000}, triggers=triggers
    )
    assert isinstance(frequencies["target"], float)
    assert frequencies["target"] == 1000.0
    assert isinstance(frequencies["deviant"], float)
    assert frequencies["deviant"] == 2000.0
    with pytest.raises(TypeError, match="must be an instance of"):
        _ensure_valid_frequencies("1000", triggers=triggers)
    with pytest.raises(TypeError, match="must be an instance of"):
        _ensure_valid_frequencies(
            {"target": "1000", "deviant": 2000}, triggers=triggers
        )
    with pytest.raises(
        ValueError, match="The target frequency must be strictly positive"
    ):
        _ensure_valid_frequencies({"target": 0, "deviant": 2000}, triggers=triggers)
    with pytest.raises(
        ValueError, match="The deviant frequency must be strictly positive"
    ):
        _ensure_valid_frequencies({"target": 1000, "deviant": -101}, triggers=triggers)
    with pytest.raises(ValueError, match="The target frequency '2000.0' is not in"):
        _ensure_valid_frequencies({"target": 2000, "deviant": 1000}, triggers=triggers)


def test_generate_sequence():
    """Test sequence generation."""
    if N_TARGET == 0 and N_DEVIANT == 0:
        pytest.skip("No target nor deviant stimuli.")
    sequence = generate_sequence(
        1000, 2000, triggers={"target/1000.0": 1, "deviant/2000.0": 2}
    )
    assert sequence.ndim == 1
    assert sequence.size == N_TARGET + N_DEVIANT
    assert sequence.dtype == np.int32
    unique, counts = np.unique(sequence, return_counts=True)
    for elt, count in zip(unique, counts, strict=True):
        if elt == 1:
            assert count == N_TARGET
        elif elt == 2:
            assert count == N_DEVIANT

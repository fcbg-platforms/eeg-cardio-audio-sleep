import numpy as np
import pytest

from cardio_audio_sleep.tasks._config import N_OMISSION, N_SOUND, TRIGGERS
from cardio_audio_sleep.tasks._utils import generate_sequence, get_event_name


def test_generate_sequence():
    """Test sequence generation."""
    if N_SOUND == 0 and N_OMISSION == 0:
        pytest.skip("No target nor omission stimuli.")
    sequence = generate_sequence()
    assert sequence.ndim == 1
    assert sequence.size == N_SOUND + N_OMISSION
    assert sequence.dtype == np.int32
    unique, counts = np.unique(sequence, return_counts=True)
    for elt, count in zip(unique, counts, strict=True):
        if elt == TRIGGERS["sound"]:
            assert count == N_SOUND
        elif elt == TRIGGERS["omission"]:
            assert count == N_OMISSION


def test_get_event_name():
    """Test getting event names."""
    assert get_event_name(TRIGGERS["sound"]) == "sound"
    assert get_event_name(TRIGGERS["omission"]) == "omission"
    with pytest.raises(RuntimeError, match="Unknown trigger"):
        get_event_name(1010101)

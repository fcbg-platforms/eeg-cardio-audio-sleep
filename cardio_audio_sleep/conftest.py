from __future__ import annotations  # c.f. PEP 563, PEP 649

from pathlib import Path
from typing import TYPE_CHECKING

from mne.io import read_raw_fif
from mne_lsl.player import PlayerLSL
from pytest import fixture

if TYPE_CHECKING:
    from pytest import Config


def pytest_configure(config: Config) -> None:
    """Configure pytest options."""
    warnings_lines = r"""
    error::
    """
    for warning_line in warnings_lines.split("\n"):
        warning_line = warning_line.strip()
        if warning_line and not warning_line.startswith("#"):
            config.addinivalue_line("filterwarnings", warning_line)


@fixture(scope="session")
def mock_ecg_stream():
    """Create a mock stream with an 'ECG' channel."""
    fname = Path(__file__).parents[1] / "data" / "ecg1024-raw.fif"
    raw = read_raw_fif(fname, preload=True)
    raw.apply_function(lambda x: x * 1e-6)  # convert to SI
    player = PlayerLSL(raw, name="mock-ECG")
    player.set_channel_units({"ECG": "microvolt"})
    yield player
    player.stop()

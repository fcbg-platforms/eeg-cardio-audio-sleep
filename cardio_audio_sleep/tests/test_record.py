from __future__ import annotations

import multiprocessing as mp
import time
import uuid
from typing import TYPE_CHECKING

import numpy as np
import pytest
from mne import create_info
from mne.io import RawArray, read_raw_fif
from mne.io.base import BaseRaw
from mne_lsl.stream import StreamLSL
from numpy.testing import assert_allclose

from resp_audio_sleep.record import Recorder

if TYPE_CHECKING:
    from pathlib import Path

    from mne.io import BaseRaw


@pytest.fixture(scope="module")
def raw_samples() -> BaseRaw:
    """Create raw with samples in data array for testing."""
    info = create_info(3, 100, ["eeg"] * 3)
    data = np.vstack((np.arange(1000), np.arange(1000), np.arange(1000)))
    raw = RawArray(data, info)
    return raw


def _player_mock_lsl_stream(
    raw: BaseRaw,
    name: str,
    source_id: str,
    status: mp.managers.ValueProxy,
) -> None:
    """Player for the 'mock_lsl_stream' fixture."""
    from mne_lsl.player import PlayerLSL  # noqa: E402

    player = PlayerLSL(raw, chunk_size=200, name=name, source_id=source_id)
    player.start()
    status.value = 1
    while status.value:
        time.sleep(0.1)
    player.stop()


@pytest.fixture
def _mock_lsl_stream(raw_samples, request):
    """Create a mock LSL stream for testing."""
    manager = mp.Manager()
    status = manager.Value("i", 0)
    name = f"P_{request.node.name}"
    source_id = uuid.uuid4().hex
    process = mp.Process(
        target=_player_mock_lsl_stream,
        args=(raw_samples, name, source_id, status),
    )
    process.start()
    while status.value != 1:
        pass
    yield
    status.value = 0
    process.join(timeout=2)
    process.kill()


@pytest.mark.usefixtures("_mock_lsl_stream")
def test_recorder(raw_samples: BaseRaw, tmp_path: Path):
    """Test the recorder class."""
    stream = StreamLSL(bufsize=4).connect(acquisition_delay=0)
    assert stream.ch_names == raw_samples.ch_names
    channels = [stream.ch_names[0], stream.ch_names[-1]]
    recorder = Recorder(stream, channels, bufsize=10)
    assert recorder._start == 0
    while stream._n_new_samples == 0:
        stream.acquire()
        time.sleep(0.1)
    recorder.get_data(n_samples=stream._n_new_samples)
    time.sleep(0.5)
    start = recorder._start
    assert 0 < start
    while stream._n_new_samples == 0:
        stream.acquire()
        time.sleep(0.1)
    recorder.get_data(n_samples=stream._n_new_samples)
    assert start < recorder._start
    # add annotations and save
    recorder.annotate(-recorder._start + 1, "test")
    recorder.annotate(0, "test2")
    recorder.save(tmp_path / "test-raw.fif")
    assert (tmp_path / "test-raw.fif").exists()
    raw = read_raw_fif(tmp_path / "test-raw.fif")
    assert raw.ch_names == channels
    # compare data arrays
    data = raw.get_data()
    expected = np.vstack((np.arange(data.shape[1]), np.arange(data.shape[1]))).astype(
        data.dtype
    )
    expected += data[0, 0]  # initial offset
    assert_allclose(data, expected)
    # compare annotations
    assert list(raw.annotations.description) == ["test", "test2"]
    assert_allclose(raw.annotations.duration, np.zeros(2))
    assert_allclose(raw.annotations.onset, [raw.times[0], raw.times[-1]])

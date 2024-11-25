from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

import numpy as np
from mne import Annotations, pick_info
from mne._fiff.pick import _picks_to_idx
from mne.io import RawArray
from mne_lsl.stream import StreamLSL

from .utils._checks import check_type, check_value, ensure_path
from .utils.logs import warn

if TYPE_CHECKING:
    from pathlib import Path


class Recorder:
    """Recorder object attached to an LSL stream.

    Parameters
    ----------
    stream : StreamLSL
        Stream from which data is recorded.
    channels : list of str | tuple of str
        List of channel names to record.
    bufsize : float
        Buffer size in seconds to record.
    """

    def __init__(
        self, stream: StreamLSL, channels: list[str] | tuple[str], bufsize: float
    ) -> None:
        check_type(stream, (StreamLSL,), "stream")
        check_type(channels, (list, tuple), "channels")
        for ch in channels:
            check_type(ch, (str,), "channel")
            check_value(ch, stream.ch_names, "channel")
        check_type(bufsize, ("numeric",), "bufsize")
        if bufsize <= 0:
            raise ValueError("The argument 'bufsize' must be positive.")
        self._stream = stream
        self._channels = channels
        self._buffer = np.zeros(
            (len(channels), ceil(bufsize * stream._info["sfreq"])),
            dtype=self._stream.dtype,
        )
        self._start = 0
        self._annotations_onset = []
        self._annotations_description = []

    def get_data(self, n_samples: int) -> None:
        """Acquire new data from the stream buffer in the recorder buffer.

        Parameters
        ----------
        n_samples : int
            The number of samples to acquire.
        """
        winsize = n_samples / self._stream._info["sfreq"]
        data, _ = self._stream.get_data(winsize=winsize, picks=self._channels)
        if self._start == self._buffer.shape[1]:
            warn("The buffer is full. Skipping.")
            return
        stop = (
            self._buffer.shape[1]
            if self._buffer.shape[1] < self._start + data.shape[1]
            else self._start + data.shape[1]
        )
        self._buffer[:, self._start : stop] = data[:, : stop - self._start]
        self._start = stop

    def annotate(self, offset: int, description: str) -> None:
        """Add an annotation on the current buffer index.

        Parameters
        ----------
        offset : int
            Offset compared to the current buffer index.
        description : str
            Description of the annotation.
        """
        offset = int(offset)
        if self._start + offset < 0 or self._buffer.shape[1] <= self._start + offset:
            raise ValueError("The offset yields an out-of-bound index.")
        self._annotations_onset.append(self._start + offset - 1)
        self._annotations_description.append(description)

    def save(self, fname: str | Path, *, overwrite: bool = False) -> None:
        """Save the buffer to a FIF file.

        Parameters
        ----------
        fname : str | Path
            Path to the FIF file used to save the buffer.
        overwrite : bool
            If True, overwrite the file if it already exists.
        """
        fname = ensure_path(fname, must_exist=False)
        check_type(overwrite, (bool,), "overwrite")
        if fname.suffix != ".fif":
            raise ValueError("The file extension must be '.fif'.")
        info = pick_info(
            self._stream._info, _picks_to_idx(self._stream._info, self._channels)
        )
        info["device_info"] = None
        raw = RawArray(self._buffer[:, : self._start], info, verbose="WARNING")
        if len(self._annotations_onset) != 0:
            assert len(self._annotations_onset) == len(self._annotations_description)
            raw.set_annotations(
                Annotations(
                    np.array(self._annotations_onset) / self._stream._info["sfreq"],
                    [0] * len(self._annotations_onset),
                    self._annotations_description,
                )
            )
        raw.save(fname, overwrite=overwrite)

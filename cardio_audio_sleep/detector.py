from __future__ import annotations

from time import sleep
from typing import TYPE_CHECKING

import numpy as np
from mne_lsl.stream import StreamLSL
from scipy.signal import find_peaks

from ._config import RECORDER_BUFSIZE, TRG_CHANNEL
from .record import Recorder
from .utils._checks import check_type
from .utils._docs import fill_doc
from .utils.logs import logger
from .viz import Viewer

if TYPE_CHECKING:
    from numpy.typing import NDArray


_BUFSIZE: float = 4.0
# number of consecutive windows in which a peak has to be detected to be considered
_N_CONSECUTIVE_WINDOWS: int = 2


@fill_doc
class Detector:
    """Real-time single channel peak detector.

    Parameters
    ----------
    %(stream_name)s
    %(ecg_ch_name)s
    ecg_height : float
        The height of the ECG peaks as a percentage of the data range, between 0 and 1.
    ecg_distance : float
        The minimum distance between two ECG peaks in seconds.
    ecg_prominence : float | None
        The minimum prominence of the ECG peaks. Can be set to None which will disable
        the prominence constraint.
    detrend : bool
        If True, apply a linear detrending prior to peak detection.
    viewer : bool
        If True, a viewer will be created to display the real-time signal and detected
        peaks. Useful for debugging or calibration, but should be set to False for
        production.
    recorder : bool
        If True, a recorder is started. Useful for debugging, but should be set to False
        for production.
    """

    def __init__(
        self,
        stream_name: str,
        ecg_ch_name: str,
        ecg_height: float,
        ecg_distance: float,
        ecg_prominence: float | None = None,
        *,
        detrend: bool = True,
        viewer: bool = False,
        recorder: bool = False,
    ) -> None:
        check_type(ecg_ch_name, (str,), "ecg_ch_name")
        check_type(ecg_height, ("numeric",), "ecg_height")
        if not 0 <= ecg_height <= 1:
            raise ValueError("ECG height must be between 0 and 1.")
        check_type(ecg_distance, ("numeric",), "ecg_distance")
        if ecg_distance <= 0:
            raise ValueError("ECG distance must be positive.")
        if ecg_prominence is not None:
            check_type(ecg_prominence, ("numeric",), "ecg_prominence")
            if ecg_prominence <= 0:
                raise ValueError("ECG prominence must be positive.")
        check_type(detrend, (bool,), "detrend")
        check_type(viewer, (bool,), "viewer")
        check_type(recorder, (bool,), "recorder")
        self._ecg_ch_name = ecg_ch_name
        self._ecg_height = ecg_height
        self._ecg_distance = ecg_distance
        self._ecg_prominence = ecg_prominence
        self._create_stream(_BUFSIZE, stream_name, recorder)
        self._detrend = detrend
        self._viewer = Viewer(ecg_ch_name, self._ecg_height) if viewer else None
        self._recorder = (
            Recorder(self._stream, [TRG_CHANNEL, ecg_ch_name], bufsize=RECORDER_BUFSIZE)
            if recorder
            else None
        )
        # peak detection settings
        self._last_peak = None
        self._peak_candidates = None
        self._peak_candidates_count = None

    @fill_doc
    def _create_stream(self, bufsize: float, stream_name: str, recorder: bool) -> None:
        """Create the LSL stream and prefill the buffer.

        Parameters
        ----------
        bufsize : float
            Size of the buffer in seconds. The buffer will be filled on instantiation,
            thus the program will hold during this duration.
        %(stream_name)s
        recorder : bool
            If True, a recorder will be attached to the stream and the channel selection
            differs.
        """
        self._stream = StreamLSL(bufsize, name=stream_name).connect(
            acquisition_delay=None, processing_flags="all"
        )
        if recorder:
            self._stream.pick([TRG_CHANNEL, self._ecg_ch_name])
            self._stream.set_channel_types(
                {TRG_CHANNEL: "stim"}, on_unit_change="ignore"
            )
        else:
            self._stream.pick(self._ecg_ch_name)
        self._stream.set_channel_types(
            {self._ecg_ch_name: "misc"}, on_unit_change="ignore"
        )
        self._stream.notch_filter(50, picks=self._ecg_ch_name)
        self._stream.notch_filter(100, picks=self._ecg_ch_name)
        logger.info("Prefilling buffer of %.2f seconds.", self._stream._bufsize)
        while self._stream._n_new_samples < self._stream._timestamps.size:
            self._stream._acquire()
            sleep(0.01)
        logger.info("Buffer prefilled.")

    @fill_doc
    def _detect_peaks(self) -> NDArray[np.float64]:
        """Acquire new samples and detect all peaks in the buffer.

        If a buffer was already processed, it will not be re-processed.

        Returns
        -------
        peaks : array of shape (n_peaks,)
            The timestamps of all detected peaks.
        """
        self._stream._acquire()
        if self._stream._n_new_samples == 0:
            return np.array([])  # nothing new to do
        if self._recorder is not None:
            self._recorder.get_data(self._stream._n_new_samples)
        data, ts = self._stream.get_data(picks=self._ecg_ch_name)
        data = data.squeeze()
        # linear detrending
        if self._detrend:
            z = np.polyfit(ts, data, 1)
            data -= z[0] * ts + z[1]
        # peak detection
        peaks, _ = find_peaks(
            data,
            height=np.percentile(data, self._ecg_height * 100),
            distance=self._ecg_distance * self._stream._info["sfreq"],
            prominence=self._ecg_prominence,
        )
        if self._viewer is not None:
            self._viewer.plot(ts, data)
        return ts[peaks]

    @fill_doc
    def new_peak(self) -> float | None:
        """Detect new peak entering the buffer.

        Returns
        -------
        peak : float | None
            The timestamp of the newly detected peak. None if no new peak is detected.
        """
        ts_peaks = self._detect_peaks()
        if ts_peaks.size == 0:
            return None
        if self._peak_candidates is None and self._peak_candidates_count is None:
            self._peak_candidates = list(ts_peaks)
            self._peak_candidates_count = [1] * ts_peaks.size
            return None
        peaks2append = []
        for k, peak in enumerate(self._peak_candidates):
            if peak in ts_peaks:
                self._peak_candidates_count[k] += 1
            else:
                peaks2append.append(peak)
        # before going further, let's make sure we don't add too many false positives
        if int(self._stream._bufsize * (1 / self._ecg_distance)) < len(
            peaks2append
        ) + len(self._peak_candidates):
            self._peak_candidates = None
            self._peak_candidates_count = None
            return None
        self._peak_candidates.extend(peaks2append)
        self._peak_candidates_count.extend([1] * len(peaks2append))
        # now, all the detected peaks have been triage, let's see if we have a winner
        idx = [
            k
            for k, count in enumerate(self._peak_candidates_count)
            if _N_CONSECUTIVE_WINDOWS == count
        ]
        if len(idx) == 0:
            return None
        peaks = sorted([self._peak_candidates[k] for k in idx])
        # compare the winner with the last known peak
        if self._last_peak is None:  # don't return the first peak detected
            new_peak = None
            self._last_peak = peaks[-1]
        if self._last_peak is None or self._last_peak + self._ecg_distance <= peaks[-1]:
            new_peak = peaks[-1]
            self._last_peak = peaks[-1]
            if self._viewer is not None:
                self._viewer.add_peak(new_peak)
        else:
            new_peak = None
        # reset the peak candidates
        self._peak_candidates = None
        self._peak_candidates_count = None
        return new_peak

    @property
    def recorder(self) -> Recorder | None:
        """The attached recorder instance."""
        return self._recorder

    @property
    def viewer(self) -> Viewer | None:
        """The attached viewer instance."""
        return self._viewer

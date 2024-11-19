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
    %(resp_ch_name)s
    ecg_height : float | None
        The height of the ECG peaks as a percentage of the data range, between 0 and 1.
    ecg_distance : float | None
        The minimum distance between two ECG peaks in seconds.
    ecg_prominence : float | None
        The minimum prominence of the ECG peaks. Can be set to None which will disable
        the prominence constraint.
    resp_prominence : float | None
        The minimum prominence of the respiration peaks.
    resp_distance : float | None
        The minimum distance between two respiration peaks in seconds.
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
        ecg_ch_name: str | None,
        resp_ch_name: str | None,
        ecg_height: float | None = None,
        ecg_distance: float | None = None,
        ecg_prominence: float | None = None,
        resp_prominence: float | None = None,
        resp_distance: float | None = None,
        *,
        detrend: bool = True,
        viewer: bool = False,
        recorder: bool = False,
    ) -> None:
        if ecg_ch_name is None and resp_ch_name is None:
            raise ValueError(
                "At least one of 'ecg_ch_name' or 'resp_ch_name' must be set."
            )
        check_type(detrend, (bool,), "detrend")
        check_type(viewer, (bool,), "viewer")
        check_type(recorder, (bool,), "recorder")
        self._ecg_ch_name = ecg_ch_name
        self._resp_ch_name = resp_ch_name
        self._set_peak_detection_parameters(
            ecg_height, ecg_distance, ecg_prominence, resp_distance, resp_prominence
        )
        self._create_stream(_BUFSIZE, stream_name, recorder)
        self._detrend = detrend
        self._viewer = (
            Viewer(ecg_ch_name, resp_ch_name, self._ecg_height) if viewer else None
        )
        if recorder:
            channels = [TRG_CHANNEL]
            if ecg_ch_name is not None:
                channels.append(ecg_ch_name)
            if resp_ch_name is not None:
                channels.append(resp_ch_name)
            self._recorder = Recorder(self._stream, channels, bufsize=RECORDER_BUFSIZE)
        else:
            self._recorder = None
        # peak detection settings
        self._last_peak = {"ecg": None, "resp": None}
        self._peak_candidates = {"ecg": None, "resp": None}
        self._peak_candidates_count = {"ecg": None, "resp": None}

    @fill_doc
    def _check_ch_type(self, ch_type) -> None:
        """Check validity of 'ch_type'.

        Parameters
        ----------
        %(ch_type)s
        """
        if ch_type not in ("resp", "ecg"):
            raise ValueError("The channel type must be either 'resp' or 'ecg'.")
        elif ch_type == "resp" and self._resp_ch_name is None:
            raise ValueError("No respiration channel was set.")
        elif ch_type == "ecg" and self._ecg_ch_name is None:
            raise ValueError("No ECG channel was set.")

    def _set_peak_detection_parameters(
        self,
        ecg_height: float | None,
        ecg_distance: float | None,
        ecg_prominence: float | None,
        resp_distance: float | None,
        resp_prominence: float | None,
    ) -> None:
        """Check validity of peak detection parameters."""
        if self._ecg_ch_name is None and any(
            elt is not None for elt in (ecg_height, ecg_distance, ecg_prominence)
        ):
            raise ValueError(
                "ECG peak detection parameters were set without ECG channel."
            )
        elif self._ecg_ch_name is not None and any(
            elt is None for elt in (ecg_height, ecg_distance)
        ):
            raise ValueError(
                "ECG peak detection parameters were not set while ECG channel was set."
            )
        if self._resp_ch_name is None and any(
            elt is not None for elt in (resp_distance, resp_prominence)
        ):
            raise ValueError(
                "Respiration peak detection parameters were set without respiration "
                "channel."
            )
        elif self._resp_ch_name is not None and any(
            elt is None for elt in (resp_distance, resp_prominence)
        ):
            raise ValueError(
                "Respiration peak detection parameters were not set while respiration "
                "channel was set."
            )
        if self._ecg_ch_name is not None:
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
        if self._resp_ch_name is not None:
            check_type(resp_distance, ("numeric",), "resp_distance")
            if resp_distance <= 0:
                raise ValueError("Respiration distance must be positive.")
            check_type(resp_prominence, ("numeric",), "resp_prominence")
            if resp_prominence <= 0:
                raise ValueError("Respiration prominence must be positive.")
        self._distances = {"ecg": ecg_distance, "resp": resp_distance}
        self._prominences = {"ecg": ecg_prominence, "resp": resp_prominence}
        self._ecg_height = ecg_height

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
        picks = [
            elt for elt in (self._ecg_ch_name, self._resp_ch_name) if elt is not None
        ]
        self._stream = StreamLSL(bufsize, name=stream_name).connect(
            acquisition_delay=0, processing_flags="all"
        )
        if recorder:
            self._stream.pick(picks + [TRG_CHANNEL])
            self._stream.set_channel_types(
                {TRG_CHANNEL: "stim"}, on_unit_change="ignore"
            )
        else:
            self._stream.pick(picks)
        self._stream.set_channel_types(
            {ch: "misc" for ch in picks}, on_unit_change="ignore"
        )
        self._stream.notch_filter(50, picks=picks)
        self._stream.notch_filter(100, picks=picks)
        if self._resp_ch_name is not None:
            self._stream.filter(None, 20, picks=self._resp_ch_name)
        logger.info("Prefilling buffer of %.2f seconds.", self._stream._bufsize)
        while self._stream._n_new_samples < self._stream._timestamps.size:
            self._stream._acquire()
            sleep(0.01)
        logger.info("Buffer prefilled.")

    @fill_doc
    def _detect_peaks(self, ch_type: str) -> NDArray[np.float64]:
        """Acquire new samples and detect all peaks in the buffer.

        If a buffer was already processed, it will not be re-processed.

        Parameters
        ----------
        %(ch_type)s

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
        data, ts = self._stream.get_data(
            picks=self._resp_ch_name if ch_type == "resp" else self._ecg_ch_name
        )
        data = data.squeeze()
        # linear detrending
        if self._detrend:
            z = np.polyfit(ts, data, 1)
            data -= z[0] * ts + z[1]
        # channel-specific settings
        if ch_type == "ecg":
            kwargs = {"height": np.percentile(data, self._ecg_height * 100)}
        # peak detection
        peaks, _ = find_peaks(
            data,
            distance=self._distances[ch_type] * self._stream._info["sfreq"],
            prominence=self._prominences[ch_type],
            **kwargs,
        )
        if self._viewer is not None:
            self._viewer.plot(ts, data, ch_type)
        return ts[peaks]

    @fill_doc
    def new_peak(self, ch_type: str) -> float | None:
        """Detect new peak entering the buffer.

        Parameters
        ----------
        %(ch_type)s

        Returns
        -------
        peak : float | None
            The timestamp of the newly detected peak. None if no new peak is detected.
        """
        self._check_ch_type(ch_type)
        ts_peaks = self._detect_peaks(ch_type)
        if ts_peaks.size == 0:
            return None
        if (
            self._peak_candidates[ch_type] is None
            and self._peak_candidates_count[ch_type] is None
        ):
            self._peak_candidates[ch_type] = list(ts_peaks)
            self._peak_candidates_count[ch_type] = [1] * ts_peaks.size
            return None
        peaks2append = []
        for k, peak in enumerate(self._peak_candidates[ch_type]):
            if peak in ts_peaks:
                self._peak_candidates_count[ch_type][k] += 1
            else:
                peaks2append.append(peak)
        # before going further, let's make sure we don't add too many false positives
        if int(self._stream._bufsize * (1 / self._distances[ch_type])) < len(
            peaks2append
        ) + len(self._peak_candidates[ch_type]):
            self._peak_candidates[ch_type] = None
            self._peak_candidates_count[ch_type] = None
            return None
        self._peak_candidates[ch_type].extend(peaks2append)
        self._peak_candidates_count[ch_type].extend([1] * len(peaks2append))
        # now, all the detected peaks have been triage, let's see if we have a winner
        idx = [
            k
            for k, count in enumerate(self._peak_candidates_count[ch_type])
            if _N_CONSECUTIVE_WINDOWS == count
        ]
        if len(idx) == 0:
            return None
        peaks = sorted([self._peak_candidates[ch_type][k] for k in idx])
        # compare the winner with the last known peak
        if self._last_peak[ch_type] is None:  # don't return the first peak detected
            new_peak = None
            self._last_peak[ch_type] = peaks[-1]
        if (
            self._last_peak[ch_type] is None
            or self._last_peak[ch_type] + self._distances[ch_type] <= peaks[-1]
        ):
            new_peak = peaks[-1]
            self._last_peak[ch_type] = peaks[-1]
            if self._viewer is not None:
                self._viewer.add_peak(new_peak, ch_type)
        else:
            new_peak = None
        # reset the peak candidates
        self._peak_candidates[ch_type] = None
        self._peak_candidates_count[ch_type] = None
        return new_peak

    @property
    def recorder(self) -> Recorder | None:
        """The attached recorder instance."""
        return self._recorder

    @property
    def viewer(self) -> Viewer | None:
        """The attached viewer instance."""
        return self._viewer

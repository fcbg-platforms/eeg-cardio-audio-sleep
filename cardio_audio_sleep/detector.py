"""Heartbeat detector, detecting R-peak entering an LSL buffer."""

import math
import xml.etree.ElementTree as ET
from typing import Optional, Union

import numpy as np
from bsl.lsl import StreamInlet, resolve_streams
from bsl.utils import Timer
from mne.filter import filter_data
from scipy.signal import find_peaks

from .utils._checks import _check_type, _check_value
from .utils._logs import logger


class Detector:
    """Class detecting R-peaks from an ECG LSL stream.

    Parameters
    ----------
    stream_name : str
        Name of the LSL stream to connect to.
    ecg_ch_name : str
        Name of the ECG channel in the LSL stream.
    duration_buffer : float
        The duration of the data buffer.
    peak_height_perc : float
        Minimum height of the peak expressed as a percentile of the samples in
        the buffer. Default to 98%.
    peak_prominence : float | None
        Minimum peak prominence as defined by scipy. Default to 700.
    peak_width : float | None
        Minimum peak width expressed in ms. Default to None.
    """

    def __init__(
        self,
        stream_name: str,
        ecg_ch_name: str,
        duration_buffer: float = 4.0,
        peak_height_perc: float = 98.0,
        peak_prominence: Optional[float] = 20.0,
        peak_width: Optional[float] = None,
    ):
        # Check arguments and create StreamReceiver
        self._peak_height_perc = Detector._check_peak_height_perc(
            peak_height_perc
        )
        self._peak_width = Detector._check_peak_width(peak_width)
        self._peak_prominence = Detector._check_peak_prominence(
            peak_prominence
        )
        _check_type(stream_name, (str,), item_name="stream_name")
        _check_type(ecg_ch_name, (str,), item_name="ecg_ch_name")
        _check_type(duration_buffer, ("numeric",), item_name="duration_buffer")
        if duration_buffer <= 0.2:
            raise ValueError(
                "Argument 'duration_buffer' must be strictly larger than 0.2. "
                f"Provided: '{duration_buffer}' seconds."
            )

        sinfos = list()
        while len(sinfos) == 0:
            sinfos = resolve_streams(timeout=10, name=stream_name)
        assert len(sinfos) == 1

        self._inlet = StreamInlet(
            sinfos[0],
            max_buffered=10,
            processing_flags=["clocksync", "dejitter", "monotize"],
        )
        self._inlet.open_stream()
        self._stream_name = stream_name

        root = ET.fromstring(self._inlet.get_sinfo().as_xml)
        ch_list = []
        for elt in root.iter("channel"):
            ch_list.append(elt.find("label").text)
        _check_value(
            ecg_ch_name,
            ch_list,
            item_name="ecg_ch_name",
        )

        # Infos from stream
        self._sample_rate = int(self._inlet.sfreq)
        self._ecg_channel_idx = ch_list.index(ecg_ch_name)
        self._ecg_channel_name = ch_list[self._ecg_channel_idx]

        # Variables
        self._duration_buffer = float(duration_buffer)
        self._duration_buffer_samples = math.ceil(
            self._duration_buffer * self._sample_rate
        )

        # Buffers
        self._timestamps_buffer = np.zeros(
            self._duration_buffer_samples, dtype=np.float32
        )
        self._ecg_buffer = np.zeros(
            self._duration_buffer_samples, dtype=np.float32
        )

        # R-Peak detectors
        self._last_peak = None
        self._peak_width_samples = Detector._convert_peak_width_to_samples(
            self._peak_width, self._sample_rate
        )
        logger.info(
            "R-peak detector with sample rate %s Hz initialized.",
            self._sample_rate,
        )

    def prefill_buffer(self) -> None:
        """Prefill an entire buffer.

        Avoids any discontinuities in the ECG buffer.
        """
        logger.info(
            "Filling an entire buffer of %s seconds..", self._duration_buffer
        )
        timer = Timer()
        while timer.sec() <= self._duration_buffer:
            self.update_loop()
        logger.info("Buffer pre-filled, ready to start!")

    def update_loop(self) -> None:
        """Update loop.

        Main update loop acquiring data from the LSL stream and filling the
        detector's buffer on each call.
        """
        data_acquired, timestamps_acquired = self._inlet.pull_chunk()
        if timestamps_acquired.size == 0:
            return  # no new samples
        n = timestamps_acquired.size

        # shape (samples, )
        self._ecg_buffer = np.roll(self._ecg_buffer, -n)
        self._ecg_buffer[-n:] = data_acquired[:, self._ecg_channel_idx]

        self._timestamps_buffer = np.roll(self._timestamps_buffer, -n)
        self._timestamps_buffer[-n:] = timestamps_acquired

    def new_peaks(self):
        """Look if new R-peaks have entered the buffer."""
        peaks = self.detect_peak()
        # stop if there is no peak
        if len(peaks) == 0:
            return None

        peak = peaks[-1]
        # stop if last peak is already treated or keep track
        if self._last_peak is not None:
            if self._timestamps_buffer[peak] == self._last_peak:
                return None  # don't log the same peak
            if self._timestamps_buffer[peak] - self._last_peak <= 0.25:
                logger.debug(
                    "Skipping peak. Found: %.2f - Last: %.2f - Δ: %.2f",
                    self._timestamps_buffer[peak],
                    self._last_peak,
                    self._timestamps_buffer[peak] - self._last_peak,
                )
                return None
            self._last_peak = self._timestamps_buffer[peak]

        # skip first peak
        else:
            logger.debug("First peak found. Skipping.")
            self._last_peak = self._timestamps_buffer[peak]
            return None

        logger.debug(
            "\n--------------------------------------\n"
            "R-Peak has entered the buffer:\n"
            "Δ buffer-peak: %.4f\n"
            "--------------------------------------\n",
            self._timestamps_buffer[-1] - self._timestamps_buffer[peak],
        )

        return peak

    def detect_peak(self):
        """Detect peaks in the ECG buffer."""
        data = self.detrend_data()

        # peak detection
        peaks, _ = find_peaks(
            data,
            height=np.percentile(data, self._peak_height_perc),
            width=self._peak_width_samples,
            prominence=self._peak_prominence,
        )

        return peaks

    def filter_data(self):
        """
        Filter the ECG buffer with an acausal filter.

        Timeit
        ------
        (mean ± std. dev. of 7 runs, 100 loops each)

        Windows -- AMD 5600X - DDR4 3600 MHz
            - Data: 512 Hz - 2048 samples
              3.71 ms ± 17.7 µs per loop
            - Data: 1024 Hz - 4096 samples
              7.03 ms ± 101 µs per loop
            - Data: 2048 Hz - 8192 samples
              13.3 ms ± 44.2 µs per loop

        Linux -- i5-4590 - DDR3 1600 MHz
            - Data: 512 Hz - 2048 samples
              5 ms ± 34 µs per loop
            - Data: 1024 Hz - 4096 samples
              9.43 ms ± 83.2 µs per loop
            - Data: 2048 Hz - 8192 samples
              18.3 ms ± 102 µs per loop
        """
        return filter_data(
            self._ecg_buffer, self._sample_rate, 1.0, 15.0, phase="zero"
        )

    def detrend_data(self):
        """
        Detrend the ECG buffer with a linear trend fit.

        Timeit
        ------
        (mean ± std. dev. of 7 runs, 1000 loops each)

        Linux -- i5-4590 - DDR3 1600 MHz
            - Data: 1024 Hz - 4096 samples
              366 µs ± 707 ns per loop
        """
        times = np.linspace(0, self._duration_buffer, self._ecg_buffer.size)
        z = np.polyfit(times, self._ecg_buffer, 1)
        linear_fit = z[0] * times + z[1]
        return self._ecg_buffer - linear_fit

    def __del__(self):
        """Destructor method."""
        try:
            del self._inlet  # disconnects from the outlet
        except AttributeError:
            pass  # error raised before the inlet was created

    # --------------------------------------------------------------------
    @property
    def sr(self):
        """The connected StreamInlet."""
        return self._inlet

    @property
    def stream_name(self):
        """The connected stream."""
        return self._stream_name

    @property
    def sample_rate(self):
        """The connected stream sample rate."""
        return self._sample_rate

    @property
    def ecg_ch_name(self):
        """The ECG channel name."""
        return self._ecg_ch_name

    @property
    def ecg_channel_idx(self):
        """The ECG channel idx."""
        return self._ecg_channel_idx

    @property
    def duration_buffer(self):
        """The duration of the buffer in seconds."""
        return self._duration_buffer

    @property
    def duration_buffer_samples(self):
        """The duration of the buffer in samples."""
        return self._duration_buffer_samples

    @property
    def timestamps_buffer(self):
        """The LSL timestamp buffer."""
        return self._timestamps_buffer

    @property
    def ecg_buffer(self):
        """The ECG samples buffer."""
        return self._ecg_buffer

    @property
    def peak_height_perc(self):
        """The minimum peak height as a percentile of the data."""
        return self._peak_height_perc

    @property
    def peak_width(self):
        """The minimum peak width in samples."""
        return self._peak_width

    @property
    def peak_prominence(self):
        """The peak prominence."""
        return self._peak_prominence

    # --------------------------------------------------------------------
    @staticmethod
    def _check_peak_height_perc(peak_height_perc: Union[int, float]):
        """Check argument 'peak_height_perc'."""
        _check_type(
            peak_height_perc, ("numeric",), item_name="peak_height_perc"
        )
        if peak_height_perc <= 0:
            raise ValueError(
                "Argument 'peak_height_perc' must be a strictly positive "
                f"number. Provided: '{peak_height_perc}%'."
            )
        if 100 <= peak_height_perc:
            raise ValueError(
                "Argument 'peak_height_perc' must be a percentage between "
                f"0 and 100 excluded. Provided '{peak_height_perc}%'."
            )
        return float(peak_height_perc)

    @staticmethod
    def _check_peak_width(peak_width: Optional[Union[int, float]]):
        """Check argument 'peak_width'."""
        _check_type(peak_width, ("numeric", None), item_name="peak_width")
        if peak_width is None:
            return None
        if peak_width <= 0:
            raise ValueError(
                "Argument 'peak_width' must be a strictly positive "
                f"number. Provided: '{peak_width}%'."
            )
        return float(peak_width)

    @staticmethod
    def _convert_peak_width_to_samples(peak_width: Optional[float], fs: float):
        """Convert a peak width from ms to samples."""
        if peak_width is None:
            return None
        else:
            return math.ceil(peak_width / 1000 * fs)

    @staticmethod
    def _check_peak_prominence(peak_prominence: Optional[Union[int, float]]):
        """Check argument 'peak_prominence'."""
        _check_type(
            peak_prominence, ("numeric", None), item_name="peak_prominence"
        )
        if peak_prominence is None:
            return None
        if peak_prominence <= 0:
            raise ValueError(
                "Argument 'peak_prominence' must be a strictly positive "
                f"number. Provided: '{peak_prominence}'."
            )
        return float(peak_prominence)

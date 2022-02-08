import math

from bsl import StreamReceiver
from bsl.utils import Timer
import numpy as np
from scipy.signal import find_peaks

from . import logger
from .utils._checks import _check_type, _check_value


class Detector:
    """
    Class detecting R-peaks from an ECG LSL stream.
    Adapted from BSL StreamViewer scope.

    Parameters
    ----------
    stream_name : str
        Name of the LSL stream to connect to.
    ecg_ch_name : str
        Name of the ECG channel in the LSL stream.
    duration_buffer : float
        The duration of the data buffer.
    """

    def __init__(self, stream_name, ecg_ch_name, duration_buffer=5):
        # Check arguments and create StreamReceiver
        _check_type(stream_name, (str, ), item_name='stream_name')
        _check_type(ecg_ch_name, (str, ), item_name='ecg_ch_name')
        _check_type(duration_buffer, ('numeric', ),
                    item_name='duration_buffer')
        if duration_buffer <= 0.2:
            raise ValueError(
                "Argument 'duration_buffer' must be strictly larger than 0.2. "
                f"Provided: '{duration_buffer}' seconds.")
        self._sr = StreamReceiver(bufsize=0.2, winsize=0.2)
        if len(self._sr.streams) == 0:
            raise ValueError(
                'The StreamReceiver did not connect to any streams.')
        _check_value(stream_name, self._sr.streams, item_name='stream_name')
        self._stream_name = stream_name
        _check_value(ecg_ch_name, self._sr.streams[stream_name].ch_list,
                     item_name='ecg_ch_name')

        # Infos from stream
        self._sample_rate = int(
            self._sr.streams[self._stream_name].sample_rate)
        self._ecg_channel_idx = \
            self._sr.streams[self._stream_name].ch_list.index(ecg_ch_name)

        # Variables
        self._duration_buffer = float(duration_buffer)
        self._duration_buffer_samples = math.ceil(
            self._duration_buffer*self._sample_rate)

        # Buffers
        self._timestamps_buffer = np.zeros(self._duration_buffer_samples)
        self._ecg_buffer = np.zeros(self._duration_buffer_samples)

        # R-Peak detectors
        self._last_peak = None
        self._first_time = None  # for debug logging purposes
        logger.info('R-peak detector with sample rate %s Hz initialized.',
                    self._sample_rate)

    def prefill_buffer(self):
        """Prefill an entire buffer before starting to avoid any
        discontinuities in the ECG buffer."""
        logger.info('Filling an entire buffer of %s seconds..',
                    self._duration_buffer)
        timer = Timer()
        while timer.sec() <= self._duration_buffer:
            self.update_loop()
        logger.info('Buffer pre-filled, ready to start!')

    def update_loop(self):
        """
        Main update loop acquiring data from the LSL stream and filling the
        detector's buffer on each call.
        """
        self._sr.acquire()
        # to be changed with ._get_buffer() if latest version is used
        self._data_acquired, self._ts_list = self._sr.get_buffer(
            self._stream_name)
        self._sr.reset_buffer()
        if len(self._ts_list) == 0:
            return  # no new samples

        # shape (samples, )
        self._timestamps_buffer = np.roll(
            self._timestamps_buffer, -len(self._ts_list))
        self._timestamps_buffer[-len(self._ts_list):] = self._ts_list

        self._ecg_buffer = np.roll(self._ecg_buffer, -len(self._ts_list))
        self._ecg_buffer[-len(self._ts_list):] = \
            self._data_acquired[:, self._ecg_channel_idx]

        if self._first_time is None:
            self._first_time = self._ts_list[0]

    def new_peaks(self):
        """
        Look if new R-peaks have entered the buffer.
        """
        peaks = self._detect_peak()
        # stop if there is no peak
        if len(peaks) == 0:
            return None

        peak = peaks[-1]
        # stop if last peak is already treated or keep track
        is_last = self._timestamps_buffer[peak] == self._last_peak
        if self._last_peak is not None and is_last:
            return None
        else:
            self._last_peak = self._timestamps_buffer[peak]

        logger.debug(
            "\n--------------------------------------\n"
            "R-Peak has entered the buffer:\n"
            " - Last buffer sample: %.2f\n"
            " - Peak position: %.2f\n"
            "--------------------------------------\n"
            "Δ buffer-peak: %.4f\n"
            "--------------------------------------\n",
            self.timestamps_buffer[-1] - self._first_time,
            self.timestamps_buffer[peak] - self._first_time,
            self.timestamps_buffer[-1] - self.timestamps_buffer[peak])

        return peak

    def _detect_peak(self):
        """
        Detect peaks in the ECG buffer.
        """
        # detrending
        times = np.linspace(0, 5, self._ecg_buffer.size)
        z = np.polyfit(times, self._ecg_buffer, 1)
        linear_fit = z[0] * times + z[1]
        data = self._ecg_buffer - linear_fit

        # peak detection
        height = np.percentile(data, 98)
        peaks, _ = find_peaks(data, height=height, prominence=700)

        return peaks

    # --------------------------------------------------------------------
    @property
    def sr(self):
        """The connected StreamReceiver."""
        return self._sr

    @property
    def stream_name(self):
        """The connected stream."""
        return self._stream_name

    @property
    def ecg_ch_name(self):
        """The ECG channel name."""
        return self.sr.streams[self.stream_name].ch_list[self.ecg_channel_idx]

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

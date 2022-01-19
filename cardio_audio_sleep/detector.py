import math

from bsl import StreamReceiver
from bsl.utils import Timer
from ecgdetectors import Detectors
import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

from .utils._checks import _check_type, _check_value

_BUFFER_DURATION = 5  # seconds


class Detector:
    """
    Class detecting R-peaks from an ECG LSL stream.
    Adapted from BSL StreamViewer scope.
    Takes _BUFFER_DURATION seconds to initialize to fill an entire buffer.

    Parameters
    ----------
    stream_name : str
        Name of the LSL stream to connect to.
    ecg_ch_name : str
        Name of the ECG channel in the LSL stream.
    """

    def __init__(self, stream_name, ecg_ch_name):
        _check_type(stream_name, (str, ), item_name='stream_name')
        _check_type(ecg_ch_name, (str, ), item_name='ecg_ch_name')
        self._sr = StreamReceiver(bufsize=0.2, winsize=0.2)
        if len(self._sr.streams) == 0:
            raise ValueError(
                'The StreamReceiver did not connect to any streams.')
        _check_value(stream_name, self._sr.streams, item_name='stream_name')
        self._stream_name = stream_name

        # Infos from stream
        self._sample_rate = int(
            self._sr.streams[self._stream_name].sample_rate)
        try:
            self._ecg_channel_idx = \
                self._sr.streams[self._stream_name]._ch_list.index(ecg_ch_name)
        except ValueError:
            raise ValueError(
                f"The ECG channel '{ecg_ch_name}' could not be found in the "
                f"stream '{stream_name}'.")

        # Variables
        self._duration_buffer = _BUFFER_DURATION
        self._duration_buffer_samples = math.ceil(
            _BUFFER_DURATION*self._sample_rate)
        self._ts_list = list()  # samples that have just been acquired

        # Buffers
        self._ecg_buffer = np.zeros(self._duration_buffer_samples)
        self._timestamps_buffer = np.zeros(self._duration_buffer_samples)

        # R-Peak detectors
        self._detectors = Detectors(self._sample_rate)

        # Fill an entire buffer
        timer = Timer()
        while timer.sec() <= _BUFFER_DURATION:
            self.update_loop()

    def update_loop(self):
        """
        Main update loop acquiring data from the LSL stream and filling the
        detector's buffer on each call.
        """
        self._sr.acquire()
        # to be changed with ._get_buffer() if latest version is used
        self._data_acquired, self._ts_list = self._sr.get_buffer()
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

    def new_peaks(self):
        """
        Look if new R-peaks have entered the buffer.
        Kalidas2017 always mark right after the peak.
        """
        peaks = self._detectors.swt_detector(self._ecg_buffer)
        # stop if there is no peak
        if len(peaks) == 0:
            return False, None

        peak = peaks[-1]
        # stop if last peak is not in the latest acquired window
        if peak < self._duration_buffer_samples - len(self._ts_list):
            return False, None

        # look for actual peak location in the preceding 60 ms
        idx = math.ceil(0.06 * self._sample_rate)
        pos = peak - idx + np.argmax(self._ecg_buffer[peak-idx:peak])
        return True, pos

    @property
    def timestamps_buffer(self):
        """The LSL timestamp buffer."""
        return self._timestamps_buffer

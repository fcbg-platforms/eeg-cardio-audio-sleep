import math

from bsl import StreamReceiver
import neurokit2 as nk
import numpy as np

from .utils._checks import _check_type, _check_value

_BUFFER_DURATION = 1  # seconds


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
    """

    def __init__(self, stream_name, ecg_ch_name):
        _check_type(stream_name, (str, ), item_name='stream_name')
        _check_type(ecg_ch_name, (str, ), item_name='ecg_ch_name')
        self._sr = StreamReceiver(bufsize=0.2, winsize=0.2)
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
        """
        # timeit on 1024 samples: 134 µs ± 175 ns per loop
        # (mean ± std. dev. of 7 runs, 10000 loops each)
        clean = nk.ecg.ecg_clean(ecg_signal=self._ecg_buffer,
                                 sampling_rate=self._sample_rate,
                                 method='hamilton2002')
        # timeit on 1024 samples: 328 µs ± 925 ns per loop
        # (mean ± std. dev. of 7 runs, 1000 loops each)
        peaks = nk.ecg.ecg_findpeaks(clean,
                                     sampling_rate=self._sample_rate,
                                     method='hamilton2002')
        # check if last peak just entered the buffer
        peak = peaks['ECG_R_Peaks'][-1]
        if self._duration_buffer_samples - len(self._ts_list) < peak:
            return True
        else:
            return False

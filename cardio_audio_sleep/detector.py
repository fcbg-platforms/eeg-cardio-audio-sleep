import math

from bsl import StreamReceiver
from bsl.utils import Timer
from mne.filter import filter_data
import numpy as np
import psychtoolbox as ptb
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
    peak_height_perc : float
        Minimum height of the peak expressed as a percentile of the samples in
        the buffer. Default to 98%.
    """

    def __init__(self, stream_name, ecg_ch_name, duration_buffer=4,
                 peak_height_perc=98):
        # Check arguments and create StreamReceiver
        self._peak_height_perc = Detector._check_peak_height_perc(
            peak_height_perc)
        _check_type(stream_name, (str, ), item_name='stream_name')
        _check_type(ecg_ch_name, (str, ), item_name='ecg_ch_name')
        _check_type(duration_buffer, ('numeric', ),
                    item_name='duration_buffer')
        if duration_buffer <= 0.2:
            raise ValueError(
                "Argument 'duration_buffer' must be strictly larger than 0.2. "
                f"Provided: '{duration_buffer}' seconds.")
        self._sr = StreamReceiver(bufsize=0.2, winsize=0.2,
                                  stream_name=stream_name)
        if len(self._sr.streams) == 0:
            raise ValueError(
                'The StreamReceiver did not connect to any streams.')
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
        data_acquired, _ = self._sr.get_buffer()
        self._sr.reset_buffer()
        n = data_acquired.shape[0]  # number of acquires samples
        if n == 0:
            return  # no new samples

        # generate timestamps from local clock
        now = ptb.GetSecs()
        times = np.arange(now - (n - 1) / self._sample_rate,
                          now + 1 / self._sample_rate,
                          1 / self._sample_rate)

        # shape (samples, )
        self._ecg_buffer = np.roll(self._ecg_buffer, -n)
        self._ecg_buffer[-n:] = data_acquired[:, self._ecg_channel_idx]

        self._timestamps_buffer = np.roll(self._timestamps_buffer, -n)
        self._timestamps_buffer[-n:] = times

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
        if self._last_peak is not None:
            if self._timestamps_buffer[peak] - self._last_peak <= 0.25:
                return None
        self._last_peak = self._timestamps_buffer[peak]

        logger.debug(
            "\n--------------------------------------\n"
            "R-Peak has entered the buffer:\n"
            "Δ buffer-peak: %.4f\n"
            "--------------------------------------\n",
            self._timestamps_buffer[-1] - self._timestamps_buffer[peak])

        return peak

    def _detect_peak(self):
        """
        Detect peaks in the ECG buffer.
        """
        # --------------------- Filter ---------------------
        # timeit (mean ± std. dev. of 7 runs, 100 loops each)
        # --------------------------------------------------
        # System: Windows - AMD 5600X - DDR4 3600 MHz
        # -------------------------------------------
        # Data: 512 Hz - 2048 samples
        # 3.71 ms ± 17.7 µs per loop
        # ----------------------------
        # Data: 1024 Hz - 4096 samples
        # 7.03 ms ± 101 µs per loop
        # ----------------------------
        # Data: 2048 Hz - 8192 samples
        # 13.3 ms ± 44.2 µs per loop
        # --------------------------------------------------
        data = filter_data(self._ecg_buffer, self._sample_rate, 1., 15.,
                           phase='zero')

        # peak detection
        height = np.percentile(data, self._peak_height_perc)
        peaks, _ = find_peaks(data, height=height)

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
    def sample_rate(self):
        """The connected stream sample rate."""
        return self._sample_rate

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

    @property
    def peak_height_perc(self):
        """The minimum peak height as a percentile of the data."""
        return self._peak_height_perc

    # --------------------------------------------------------------------
    @staticmethod
    def _check_peak_height_perc(peak_height_perc):
        """Checks argument 'peak_height_perc'."""
        _check_type(peak_height_perc, ('numeric', ),
                    item_name='peak_height_perc')
        if peak_height_perc <= 0:
            raise ValueError(
                "Argument 'peak_height_perc' must be a strictly positive "
                f"number. Provided: '{peak_height_perc}%'.")
        if 100 <= peak_height_perc:
            raise ValueError(
                "Argument 'peak_height_perc' must be a percentage between "
                f"0 and 100 excluded. Provided '{peak_height_perc}%'.")
        return float(peak_height_perc)

"""
Base class for sound delivery.
"""
from abc import ABC, abstractmethod

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from ..utils._docs import fill_doc
from ..utils._checks import _check_type


@fill_doc
class _Sound(ABC):
    """
    Base audio stimulus class.

    Parameters
    ----------
    %(audio_volume)s
    %(audio_sample_rate)s
    %(audio_duration)s
    """

    @abstractmethod
    def __init__(self, volume, sample_rate=44100, duration=0.1):
        self._volume = _Sound._check_volume(volume)
        self._sample_rate = _Sound._check_sample_rate(sample_rate)
        self._duration = _Sound._check_duration(duration)
        self._time_arr = np.linspace(
            0, duration, int(duration*sample_rate), endpoint=True)
        # [:, 0] for left and [:, 1] for right
        self._signal = np.zeros(shape=(self._time_arr.size, len(self._volume)))

        self._set_signal()

    @abstractmethod
    def _set_signal(self):
        """
        Sets the signal to output.
        """
        pass

    # --------------------------------------------------------------------
    def play(self, blocking=False):
        """
        Play the sound. This function creates and terminates an audio stream.
        """
        sd.play(self._signal, samplerate=self._sample_rate, mapping=[1, 2])
        if blocking:
            sd.wait()

    def stop(self):
        """
        Stops the sounds played in the background.
        """
        sd.stop()

    def write(self, fname):
        """
        Save a sound signal into a .wav file with scipy.io.wavfile.write().

        Parameters
        ----------
        fname : str, path
            Path to the file where the sound signal is saved. The extension
            should be '.wav'.
        """
        wavfile.write(fname, self._sample_rate, self._signal)

    # --------------------------------------------------------------------
    @staticmethod
    def _check_volume(volume):
        """
        Checks that the volume is either:
            - 1 number, 1-item iterable for mono.
            - 2 numbers in a 2-item iterable for stereo.
        Checks that the volume value is between [0, 100].
        """
        _check_type(volume, (int, float, list, tuple, np.ndarray),
                    item_name='volume')
        if isinstance(volume, (int, float)):
            volume = [volume]
        assert len(volume) in (1, 2)
        for vol in volume:
            _check_type(vol, (int, float))
        assert all(0 <= v <= 100 for v in volume)
        return volume

    @staticmethod
    def _check_sample_rate(sample_rate):
        """
        Checks if the sample rate is a positive integer.
        """
        _check_type(sample_rate, ('numeric', ), item_name='sample_rate')
        assert 0 < sample_rate
        return sample_rate

    @staticmethod
    def _check_duration(duration):
        """
        Checks if the duration is positive.
        """
        _check_type(duration, ('numeric', ), item_name='duration')
        assert 0 < duration
        return duration

    # --------------------------------------------------------------------
    @property
    def volume(self):
        """
        Sound's volume(s).
        """
        return self._volume

    @volume.setter
    def volume(self, volume):
        self._volume = _Sound._check_volume(volume)
        self._signal = np.zeros(shape=(self._time_arr.size, len(self._volume)))
        self._set_signal()

    @property
    def sample_rate(self):
        """
        Sound's sampling rate [Hz].
        """
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, sample_rate):
        self._sample_rate = _Sound._check_sample_rate(sample_rate)
        self._time_arr = np.linspace(
            0, self._duration,
            int(self._duration*self._sample_rate), endpoint=True)
        self._signal = np.zeros(shape=(self._time_arr.size, len(self._volume)))
        self._set_signal()

    @property
    def duration(self):
        """
        Sound's duration [seconds].
        """
        return self._duration

    @duration.setter
    def duration(self, duration):
        self._duration = _Sound._check_duration(duration)
        self._time_arr = np.linspace(
            0, self._duration,
            int(self._duration*self._sample_rate), endpoint=True)
        self._signal = np.zeros(shape=(self._time_arr.size, len(self._volume)))
        self._set_signal()

    @property
    def signal(self):
        """
        Sound's signal.
        """
        return self._signal

"""
Sound loaded from a file.
"""
from pathlib import Path

from scipy.io import wavfile
from scipy.signal import resample

from ._sound import _Sound
from ..utils._checks import _check_type


class Sound(_Sound):
    """
    Sound loaded from file.

    Parameters
    ----------
    fname : str | Path
        Path to the supported audio file to load.
    """

    def __init__(self, fname):
        self._fname = Sound._check_file(fname)

        _original_sample_rate, _original_signal = wavfile.read(self._fname)
        self._original_sample_rate = _Sound._check_sample_rate(
            _original_sample_rate)
        self._original_signal = Sound._check_signal(_original_signal)
        self._original_duration = Sound._compute_duration(
            self._original_signal, self._original_sample_rate)

        _volume = Sound._compute_volume(self._original_signal)
        self._trim_samples = None
        super().__init__(
            _volume, self._original_sample_rate, self._original_duration)

    def _set_signal(self):
        """
        Sets the signal to output.
        """
        assert len(self._signal.shape) in (1, 2)
        slc = slice(None, self._trim_samples) \
            if len(self._original_signal.shape) == 1 \
            else (slice(None, self._trim_samples), slice(None))
        self._signal = self._original_signal[slc]

    def trim(self, duration):
        """
        Trim the original sound to the new duration.
        """
        if Sound._valid_trim_duration(duration, self._original_duration):
            self._duration = _Sound._check_duration(duration)
            self._trim_samples = int(self._duration * self._sample_rate)
            self._set_signal()

    def resample(self, sample_rate):
        """
        Resample the curent sound to the new sampling rate.
        """
        self._sample_rate = _Sound._check_sample_rate(sample_rate)
        self._signal = resample(
            self._signal, int(self._sample_rate * self._duration), axis=0)

    def reset(self):
        """
        Reset the current sound to the original loaded sound.
        """
        self._duration = self._original_duration
        self._trim_samples = None
        self._sample_rate = self._original_sample_rate
        self._set_signal()

    # --------------------------------------------------------------------
    @staticmethod
    def _check_file(fname):
        """
        Cheks if the file is supported and exists.
        """
        SUPPORTED = ('.wav')

        _check_type(fname, ('path-like', ))
        fname = Path(fname)
        assert fname.suffix in SUPPORTED and fname.exists()
        return fname

    @staticmethod
    def _check_signal(signal):
        """
        Checks that the sound is either mono or stereo.
        """
        assert len(signal.shape) in (1, 2)
        if len(signal.shape) == 2:
            assert signal.shape[1] in (1, 2)
            if signal.shape[1] == 1:
                signal = signal[:, 0]
        return signal

    @staticmethod
    def _compute_duration(signal, sample_rate):
        """
        Computes the sounds duration from the number of samples and the
        sampling rate.
        """
        return signal.shape[0] / sample_rate

    @staticmethod
    def _compute_volume(signal):
        """
        Volume modifications is not supported for loaded sounds.
        Returns [1] * number of channels.
        """
        return [1] * len(signal.shape)

    @staticmethod
    def _valid_trim_duration(trim_duration, sound_duration):
        """
        Returns True if trim_duration is smaller than sound_duration.
        """
        if sound_duration <= trim_duration:
            return False
        return True

    # --------------------------------------------------------------------
    @_Sound.volume.setter
    def volume(self, volume):
        pass

    @_Sound.sample_rate.setter
    def sample_rate(self, sample_rate):
        self.resample(sample_rate)

    @_Sound.duration.setter
    def duration(self, duration):
        self.trim(duration)

    @property
    def fname(self):
        """
        The sound's original file name.
        """
        return self._fname

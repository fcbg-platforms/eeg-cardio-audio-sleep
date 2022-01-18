"""
Pure tone sound.
"""

import numpy as np

from ._sound import _Sound
from ..utils._docs import fill_doc
from ..utils._checks import _check_type


@fill_doc
class Tone(_Sound):
    """
    Pure tone stimuli at the frequency f (Hz).
    The equation is sin(2*pi*f*time).

    Example: A 440 - La 440 - Tone(f=440)

    Parameters
    ----------
    %(audio_volume)s
    %(audio_sample_rate)s
    %(audio_duration)s
    frequency : int
        Pure tone frequency. The default is 440 Hz (La - A440).
    """

    def __init__(self, volume, sample_rate=44100, duration=0.1, frequency=440):
        self._frequency = Tone._check_frequency(frequency)
        self.name = 'tone'
        super().__init__(volume, sample_rate, duration)

    def _set_signal(self):
        """
        Sets the signal to output.
        """
        tone_arr = np.sin(2*np.pi*self._frequency*self._time_arr)

        self._signal[:, 0] = tone_arr * self._volume[0] / 100
        if len(self._volume) == 2:
            self._signal[:, 1] = tone_arr * self._volume[1] / 100

    # --------------------------------------------------------------------
    @staticmethod
    def _check_frequency(frequency):
        """
        Checks if the frequency is positive.
        """
        _check_type(frequency, ('numeric', ), item_name='frequency')
        assert 0 < frequency
        return frequency

    # --------------------------------------------------------------------
    @property
    def frequency(self):
        """
        Sound's pure tone frequency [Hz].
        """
        return self._frequency

    @frequency.setter
    def frequency(self, frequency):
        self._frequency = Tone._check_frequency(frequency)
        self._set_signal()

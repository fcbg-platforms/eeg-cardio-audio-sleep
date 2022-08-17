import sys

import numpy as np
from psychopy.clock import wait
from scipy.signal.windows import tukey

from ..config.constants import TONE_FQ


def test_volume(volume):
    """Play a pure tone at the given volume."""
    from stimuli.audio import Tone

    sound = Tone(volume, duration=0.1, frequency=TONE_FQ)
    window = tukey(sound.signal.shape[0], alpha=0.25, sym=True)
    sound._signal = np.multiply(sound.signal.T, window).T

    if sys.platform.startswith("win"):
        wait(sound.duration + 0.05, hogCPUperiod=0)
    else:
        sound.play(blocking=True)
    sound.stop()

    del sound
    del Tone

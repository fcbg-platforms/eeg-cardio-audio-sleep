import sys

from psychopy.clock import wait

from ..config.constants import TONE_FQ


def test_volume(volume):
    """Play a pure tone at the given volume."""
    from stimuli.audio import Tone

    sound = Tone(volume, duration=0.1, frequency=TONE_FQ)
    if sys.platform.startswith("win"):
        wait(0.1, hogCPUperiod=0.1)
    else:
        sound.play(blocking=True)
    sound.stop()

    del sound
    del Tone

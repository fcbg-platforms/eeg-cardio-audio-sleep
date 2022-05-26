def test_volume(volume):
    """Play a pure tone at the given volume."""
    from ..audio import Tone

    sound = Tone(volume, duration=0.1, frequency=1000)
    sound.play(blocking=True)
    sound.stop()

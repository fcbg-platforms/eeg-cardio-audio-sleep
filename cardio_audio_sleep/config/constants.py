# PsychoPy windows constants
SCREEN_SIZE: tuple[int, int] = (1920, 1080)
SCREEN_KWARGS = dict(
    size=SCREEN_SIZE,
    winType="pyglet",
    monitor=None,
    screen=1,
    fullscr=True,
    allowGUI=False,
)

# Pure tone stimuli
TONE_FQ: float = 1000  # Hz
# Serial trigger
COM_PORT: str = "/dev/ttyUSB0"
# Amplifier type
AMPLIFIER: str = "ant"

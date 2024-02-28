# PsychoPy windows constants
SCREEN_SIZE = (1920, 1080)
SCREEN_KWARGS = dict(
    size=SCREEN_SIZE,
    winType="pyglet",
    monitor=None,
    screen=1,
    fullscr=True,
    allowGUI=False,
)

# Pure tone stimuli
TONE_FQ = 1000  # Hz
# Serial trigger com port and baudrate
COM_PORT = "COM3"
COM_BAUDRATE = 9600

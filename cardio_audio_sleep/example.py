from pathlib import Path
from typing import Dict

from psychopy.clock import wait
from psychopy.hardware.keyboard import Keyboard
from psychopy.visual import ImageStim, TextStim, Window

from .utils import load_instrument_images


def example(win: Window, instrument_sounds: Dict[str, Path]):
    """Example task."""
    from stimuli.audio import Sound

    sounds = {key: Sound(path) for key, path in instrument_sounds.items()}

    try:
        # prepare keyboard for interaction
        keyboard = Keyboard()
        win.callOnFlip(keyboard.clearEvents, eventType="keyboard")
        # prepare components
        continue_text = TextStim(
            win=win,
            text="Press SPACE to continue.",
            height=0.05,
            pos=(0, -0.65),
        )
        images = load_instrument_images()
        percussion_image = ImageStim(
            win, images["percussion"], pos=(-0.5, -0.2)
        )
        string_image = ImageStim(win, images["string"], pos=(0, -0.2))
        wind_image = ImageStim(win, images["wind"], pos=(+0.5, -0.2))
        continue_text.setAutoDraw(True)
        percussion_image.setAutoDraw(True)
        string_image.setAutoDraw(True)
        wind_image.setAutoDraw(True)
        # display
        win.flip()
        # start playing sounds
        for sound in sounds:
            sound.play()
            wait(1, hogCPUperiod=0)
            sound.play()
            wait(1, hogCPUperiod=0)
        while True:  # wait for 'space'
            keys = keyboard.getKeys(keyList=["space"], waitRelease=False)
            if len(keys) != 0:
                break
            win.flip()
        # remove components
        continue_text.setAutoDraw(False)
        percussion_image.setAutoDraw(False)
        string_image.setAutoDraw(False)
        wind_image.setAutoDraw(False)
    except Exception:
        raise
    finally:
        win.flip()  # flush win.callOnFlip() and win.timeOnFlip()
        win.close()

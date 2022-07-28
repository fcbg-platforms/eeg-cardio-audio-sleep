from pathlib import Path
from typing import Dict

import numpy as np
from psychopy.clock import wait
from psychopy.hardware.keyboard import Keyboard
from psychopy.visual import ImageStim, TextStim, Window

from .utils import load_instrument_categories, load_instrument_images


def example(
    win: Window, instrument_sounds: Dict[str, Path], volume: float
):  # noqa: D401
    """Example task."""
    from stimuli.audio import Sound

    try:
        # load sounds
        instruments = load_instrument_categories()
        assert all(len(elt) == 1 for elt in instrument_sounds.values())
        sounds = sorted(
            [
                (path[0].parent.name, Sound(path[0]))
                for key, path in instrument_sounds.items()
            ],
            key=lambda x: x[0],
        )
        assert [elt[0] for elt in sounds] == instruments  # sanity-check
        sounds = [elt[1] for elt in sounds]
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
        instrument_images = load_instrument_images()
        assert sorted(instrument_images.keys()) == instruments  # sanity-check
        # determine positions
        positions = np.linspace(-0.5, 0.5, len(instruments))
        images = list()
        for instrument, position in zip(instruments, positions):
            images.append(
                ImageStim(
                    win, instrument_images[instrument], pos=(position, 0)
                )
            )
        for img in images:
            img.setAutoDraw(True)
        # display
        win.flip()
        # start playing sounds
        for sound in sounds:
            sound.volume = volume  # set volume
            sound.play()
            wait(1, hogCPUperiod=0)
            sound.play()
            wait(1, hogCPUperiod=0)
        continue_text.setAutoDraw(True)
        win.flip()
        while True:  # wait for 'space'
            keys = keyboard.getKeys(keyList=["space"], waitRelease=False)
            if len(keys) != 0:
                break
        # remove components
        continue_text.setAutoDraw(False)
        for img in images:
            img.setAutoDraw(False)
    except Exception:
        raise
    finally:
        win.flip()  # flush win.callOnFlip() and win.timeOnFlip()
        win.close()

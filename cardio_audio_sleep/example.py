import multiprocessing as mp
from pathlib import Path

import numpy as np
from psychopy.clock import wait
from psychopy.hardware.keyboard import Keyboard
from psychopy.visual import ImageStim, TextStim, Window

from .utils import load_instrument_categories, load_instrument_images


def example(win: Window, instrument_sounds: dict[str, Path], volume: float) -> None:  # noqa: D401
    """Example task."""
    try:
        # prepare keyboard for interaction
        keyboard = Keyboard()
        win.callOnFlip(keyboard.clearEvents, eventType="keyboard")
        keyboard.stop()
        # prepare components
        continue_text = TextStim(
            win=win,
            text="Press SPACE to continue.",
            height=0.05,
            pos=(0, -0.65),
        )
        instruments = load_instrument_categories()
        instrument_images = load_instrument_images()
        assert sorted(instrument_images.keys()) == instruments  # sanity-check
        # determine positions
        positions = np.linspace(-0.5, 0.5, len(instruments))
        images = list()
        for instrument, position in zip(instruments, positions, strict=True):
            images.append(
                ImageStim(win, instrument_images[instrument], pos=(position, 0))
            )
        for img in images:
            img.setAutoDraw(True)
        continue_text.setAutoDraw(True)
        # display
        win.flip()
        # start playing sounds
        process = mp.Process(target=play_sounds, args=(instrument_sounds, volume))
        process.start()
        keyboard.start()
        while True:  # wait for 'space'
            keys = keyboard.getKeys(keyList=["space"], waitRelease=False)
            if len(keys) != 0:
                process.kill()
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


def play_sounds(instrument_sounds: dict[str, Path], volume: float) -> None:
    """Play example sounds."""
    from stimuli.audio import Sound

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

    # play sounds
    for sound in sounds:
        sound.volume = volume  # set volume
        sound.play()
        wait(1, hogCPUperiod=0)
        sound.play()
        wait(1, hogCPUperiod=0)

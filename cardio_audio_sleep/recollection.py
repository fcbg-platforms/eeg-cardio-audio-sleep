import time

from psychopy.hardware.keyboard import Keyboard
from psychopy.visual import ButtonStim, ShapeStim, Slider, TextStim, Window

from .config import load_triggers
from .tasks import asynchronous, isochronous, synchronous


def recollection(win: Window, args_mapping: dict, dev: bool):
    """Recollection task."""
    # prepare keyboard for interaction
    keyboard = Keyboard()
    win.callOnFlip(keyboard.clearEvents, eventType="keyboard")
    # prepare text component for category routine
    text_category = TextStim(
        win=win,
        text="1: percussion\n2: string\n3: wind",
        height=0.05,
    )
    # load trigger values
    tdef = load_triggers()
    # run routines
    try:
        _instructions(win, keyboard)
        _fixation_cross(win)
        _category(win, keyboard, text_category)
        _confidence(win)
    except Exception:
        raise
    finally:  # close
        win.flip()  # flip one last time before closing to flush events
        win.close()


def _instructions(win: Window, keyboard: Keyboard):
    """Instruction routine."""
    text = TextStim(
        win=win,
        text="You will hear 15 pure tones followed by an instrument sound.\n"
        "After the instrument sound, enter the sound category on the "
        "keyboard:\n\n"
        "- Press 1 for percussion\n"
        "- Press 2 for string\n"
        "- Press 3 for wind\n\n"
        "Press SPACE to continue.",
        height=0.05,
    )
    text.setAutoDraw(True)
    win.flip()
    while True:  # wait for 'space'
        keys = keyboard.getKeys(keyList=["space"], waitRelease=False)
        if len(keys) != 0:
            break
        win.flip()
    text.setAutoDraw(False)


def _fixation_cross(win: Window):
    """Fixation cross routine."""
    cross = ShapeStim(
        win=win,
        vertices="cross",
        units="height",
        size=(0.05, 0.05),
        lineColor="white",
        fillColor="white",
    )
    cross.setAutoDraw(True)
    win.flip()
    time.sleep(2)
    cross.setAutoDraw(False)


def _category(win: Window, keyboard: Keyboard, text_category: TextStim):
    """Category routine."""
    text_category.setAutoDraw(True)
    win.flip()
    while True:  # wait for '1', '2', '3'
        keys = keyboard.getKeys(keyList=["1", "2", "3"], waitRelease=False)
        if len(keys) != 0:
            print([key.name for key in keys])
            break
    text_category.setAutoDraw(False)


def _confidence(win: Window):
    """Confidence routine."""
    text = TextStim(
        win=win,
        text="How confident are you?",
        height=0.05,
        pos=(0, 0.3),
    )
    slider = Slider(
        win=win,
        ticks=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        granularity=1.0,
        startValue=5,
        labels=["low", "high"],
        labelHeight=0.05,
    )
    button = ButtonStim(
        win,
        text="Confirm",
        letterHeight=0.05,
        pos=(0.5, -0.3),
        size=(0.18, 0.1),
    )
    # draw components
    text.setAutoDraw(True)
    slider.setAutoDraw(True)
    button.setAutoDraw(True)
    win.flip()
    while not button.isClicked:  # wait for button click
        win.flip()
    text.setAutoDraw(False)
    slider.setAutoDraw(False)
    button.setAutoDraw(False)

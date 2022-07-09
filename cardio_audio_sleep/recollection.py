import time

from psychopy.hardware.keyboard import Keyboard
from psychopy.visual import ButtonStim, ShapeStim, Slider, TextStim, Window


def recollection():
    """Recollection task."""
    # prepare window
    win = Window(
        size=(1024, 768),
        fullscr=True,
        screen=0,
        winType='pyglet',
        allowGUI=False,
        monitor=None,
        units='norm',
    )
    keyboard = Keyboard()
    win.callOnFlip(keyboard.clearEvents, eventType='keyboard')

    # prepare text component for category routine
    text_category = TextStim(
        win=win,
        text='1: percussion\n2: string\n3: wind',
        height=0.05,
    )
    try:
        # run routines
        _instructions(win, keyboard)
        _fixation_cross(win)
        _category(win, keyboard, text_category)
        _confidence(win)
    except Exception:
        raise
    finally:
        # close
        win.flip()  # flip one last time before closing to flush events
        win.close()


def _instructions(win: Window, keyboard: Keyboard):
    """Instruction routine."""
    text = TextStim(
        win=win,
        text='You will hear 15 pure tones followed by an instrument sound.\n'
             'After the instrument sound, enter the sound category on the '
             'keyboard:\n\n'
             '- Press 1 for percussion\n'
             '- Press 2 for string\n'
             '- Press 3 for wind\n\n'
             'Press SPACE to continue.',
        height=0.05,
    )
    text.setAutoDraw(True)
    win.flip()
    while True:  # wait for 'space'
        keys = keyboard.getKeys(keyList=['space'], waitRelease=False)
        if len(keys) != 0:
            break
        win.flip()
    text.setAutoDraw(False)


def _fixation_cross(win: Window):
    """Fixation cross routine."""
    cross = ShapeStim(
        win=win,
        vertices='cross',
        units='height',
        size=(0.05, 0.05),
        lineColor='white',
        fillColor='white',
    )
    cross.setAutoDraw(True)
    win.flip()
    time.sleep(2)
    cross.setAutoDraw(False)


def _category(win: Window, keyboard: Keyboard, text_category: TextStim):
    """Category routine."""
    # draw instructions
    text_category.setAutoDraw(True)
    win.flip()
    # wait for '1', '2', '3'
    while True:
        keys = keyboard.getKeys(keyList=['1', '2', '3'], waitRelease=False)
        if len(keys) != 0:
            print ([key.name for key in keys])
            break
    # remove instructions on next flip
    text_category.setAutoDraw(False)


def _confidence(win: Window):
    """Confidence routine."""
    text = TextStim(
        win=win,
        text='How confident are you?',
        pos=(0, 0.3),
        height=0.05,
    )
    slider = Slider(
        win=win,
        startValue=5,
        labels=["low", "high"],
        ticks=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        granularity=1.0,
        labelHeight=0.05,
    )
    button = ButtonStim(win,
        text='Confirm',
        pos=(0.5, -0.3),
        letterHeight=0.05,
        size=(0.18, 0.1),
    )
    # draw components
    text.setAutoDraw(True)
    slider.setAutoDraw(True)
    button.setAutoDraw(True)
    win.flip()
    # wait for button click
    while not button.isClicked:
        win.flip()
    # remove components on next flip
    text.setAutoDraw(False)
    slider.setAutoDraw(False)
    button.setAutoDraw(False)

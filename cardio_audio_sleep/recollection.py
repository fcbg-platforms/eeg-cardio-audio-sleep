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
        allowStencil=False,
        monitor=None,
        color=[0,0,0],
        colorSpace='rgb',
        blendMode='avg',
        useFBO=True,
        units='height',
    )
    keyboard = Keyboard()
    win.callOnFlip(keyboard.clearEvents, eventType='keyboard')

    # prepare text component for category routine
    text_category = TextStim(
        win=win,
        text='1: wind\n2: brass\n3: percussion',
        height=0.03,
    )

    # run routines
    _instructions(win, keyboard)
    _fixation_cross(win)
    _category(win, keyboard, text_category)
    _confidence(win)

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
             '- Press 1 for wind\n'
             '- Press 2 for brass\n'
             '- Press 3 for percussion\n\n'
             'Press SPACE to continue.',
        height=0.03,
    )
    # draw instructions
    text.setAutoDraw(True)
    win.flip()
    # wait for 'space'
    while True:
        keys = keyboard.getKeys(keyList=['space'], waitRelease=False)
        if len(keys) != 0:
            break
        win.flip()
    # remove instructions on next flip
    text.setAutoDraw(False)


def _fixation_cross(win: Window):
    """Fixation cross routine."""
    cross = ShapeStim(
        win=win,
        vertices='cross',
        units='height',
        size=(0.1, 0.1),
        ori=0.0,
        pos=(0, 0),
        lineWidth=1.0,
        colorSpace='rgb',
        lineColor='white',
        fillColor='white',
        opacity=None,
        depth=0.0,
        interpolate=True,
    )
    # draw cross
    cross.setAutoDraw(True)
    win.flip()
    # wait fix time
    time.sleep(2)
    # remove cross on next flip
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
        units='norm',
        height=0.03,
    )
    slider = Slider(
        win=win,
        startValue=5,
        size=(1.0, 0.1),
        pos=(0, 0),
        units="norm",
        labels=["low", "high"],
        ticks=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        granularity=1.0,
        style='rating',
        styleTweaks=(),
        opacity=None,
        color='LightGray',
        fillColor='Red',
        borderColor='White',
        colorSpace='rgb',
        font='Open Sans',
        labelHeight=0.05,
        flip=False,
        depth=-1,
        readOnly=False,
    )
    button = ButtonStim(win,
        text='Confirm',
        font='Arvo',
        pos=(0.5, -0.5),
        units='norm',
        letterHeight=0.05,
        size=(0.18, 0.1),
        borderWidth=0.0,
        fillColor='darkgrey',
        borderColor=None,
        color='white',
        colorSpace='rgb',
        opacity=None,
        bold=True,
        italic=False,
        padding=None,
        anchor='center',
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

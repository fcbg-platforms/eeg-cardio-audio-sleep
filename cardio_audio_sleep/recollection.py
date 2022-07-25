from itertools import chain
from typing import Callable, Tuple, Union

import numpy as np
from bsl.triggers import (
    LSLTrigger,
    MockTrigger,
    ParallelPortTrigger,
    TriggerDef,
)
from numpy.typing import NDArray
from psychopy.hardware.keyboard import Keyboard
from psychopy.visual import (
    ButtonStim,
    ImageStim,
    ShapeStim,
    Slider,
    TextStim,
    Window,
)

from . import logger
from .config import load_config, load_triggers
from .tasks import asynchronous, isochronous, synchronous
from .utils import (
    generate_async_timings,
    generate_sequence,
    load_instrument_categories,
    load_instrument_images,
)


def recollection(
    win: Window,
    args_mapping: dict,
    trigger: Union[MockTrigger, ParallelPortTrigger],
    trigger_instrument: LSLTrigger,
    instrument_files_sleep: dict,
    instrument_files_recollection: dict,
    dev: bool,
):
    """Recollection task."""
    # prepare keyboard for interaction
    keyboard = Keyboard()
    win.callOnFlip(keyboard.clearEvents, eventType="keyboard")
    # prepare text component for category routine
    images_category, texts_category = _prepare_category(win)

    # list out and randomize the tests
    recollection_tests = _list_recollection_tests(
        instrument_files_sleep,
        instrument_files_recollection,
        dev,
    )
    # prepare the task functions
    task_mapping = {
        "synchronous": synchronous,
        "isochronous": isochronous,
        "asynchronous": asynchronous,
    }
    # load config
    args_mapping, config, tdef = _load_config(args_mapping, dev)
    # variable to store the timings from the synchronous condition
    sequence_timings = None
    # variable to store the responses
    responses = dict(condition=[], instrument=[], category=[], confidence=[])

    # run routines
    try:
        _instructions(win, keyboard)
        for k, (condition, instrument) in enumerate(recollection_tests):
            if k != 0 and k % 24 == 0:
                _pause(win, keyboard)
            logger.info(
                "[Recollection] %i / %i : %s condition with %s sound.",
                k + 1,
                len(recollection_tests),
                condition,
                instrument.name,
            )
            # store condition and instrument name
            responses["condition"].append(condition)
            responses["instrument"].append(instrument.name)
            # prepare arguments
            args = args_mapping[condition]
            args[2] = generate_sequence(
                config[condition]["n_stimuli"],
                config[condition]["n_omissions"],
                config[condition]["edge_perc"],
                args[1],  # tdef
            )
            if condition == "isochronous":
                assert sequence_timings is not None
                args[3] = np.median(np.diff(sequence_timings))
                logger.info("Delay for isochronous: %.2f (s).", args[3])
            if condition == "asynchronous":
                timings = generate_async_timings(sequence_timings, perc=0)
                args[3] = timings
                logger.info(
                    "Average delay for asynchronous: %.2f (s).",
                    np.median(np.diff(args[3])),
                )

            # set the instrument sound
            idx = 9 if condition == "synchronous" else 5
            args[idx] = instrument
            logger.debug(
                "Instrument sound for next %s block set to %s",
                condition,
                args[idx].name,
            )
            trigger_instrument.signal(args[idx].name)

            result = _fixation_cross(
                win,
                task_mapping[condition],
                tuple(args),
                condition,
            )
            responses["category"].append(
                _category(
                    win,
                    trigger,
                    tdef,
                    keyboard,
                    images_category,
                    texts_category,
                )
            )
            responses["confidence"].append(_confidence(win))
            if result is not None:
                assert condition == "synchronous"  # sanity-check
                sequence_timings = result  # replace previous sequence timings
    except Exception:
        raise
    finally:  # close
        win.flip()  # flip one last time before closing to flush events
        win.close()
    return responses


def _list_recollection_tests(
    instrument_files_sleep: dict,
    instrument_files_recollection: dict,
    dev: bool,
):
    """List the condition/sound tests to run."""
    conditions = ("synchronous", "isochronous", "asynchronous")
    assert all(elt in instrument_files_sleep for elt in conditions)
    assert all(elt in instrument_files_recollection for elt in conditions)
    recollection_tests = list()
    for condition in conditions:
        if not dev:
            files = [
                elt
                for elt in instrument_files_sleep.values()
                if elt is not None
            ]
            for file in chain(*files):
                recollection_tests.append((condition, file))
        for file in chain(*instrument_files_recollection.values()):
            recollection_tests.append((condition, file))
    # double if not in dev mode
    if not dev:
        recollection_tests += recollection_tests
    # shuffle
    np.random.shuffle(recollection_tests)
    # make sure we are starting with a sync
    first_sync = [elt[0] for elt in recollection_tests].index("synchronous")
    recollection_tests[0], recollection_tests[first_sync] = (
        recollection_tests[first_sync],
        recollection_tests[0],
    )
    return recollection_tests


def _load_config(
    args_mapping: dict, dev: bool
) -> Tuple[dict, dict, TriggerDef]:
    """Load config and prepare arguments."""
    # load config
    config, _ = load_config("config-recollection.ini", dev)
    assert config["synchronous"]["instrument"]
    assert config["isochronous"]["instrument"]
    assert config["asynchronous"]["instrument"]
    args_mapping["synchronous"][10] = config["synchronous"]["n_instrument"]
    args_mapping["isochronous"][6] = config["isochronous"]["n_instrument"]
    args_mapping["asynchronous"][6] = config["asynchronous"]["n_instrument"]

    # load trigger
    tdef_ = load_triggers()
    key2remove = list()
    for key in tdef_.by_name:
        if "response" in key:
            continue
        key2remove.append(key)
    for key in key2remove:
        tdef_.remove(key)
    # list out instrument categories
    instrument_categories = load_instrument_categories()
    mapping = {
        f"{instrument}_response": str(k + 1)
        for k, instrument in enumerate(instrument_categories)
    }
    assert mapping == {  # hard-coded sanity-check
        "percussion_response": "1",
        "string_response": "2",
        "wind_response": "3",
    }
    tdef = TriggerDef()
    for key, value in tdef_.by_name.items():
        tdef.add(mapping[key], value)
    return args_mapping, config, tdef


def _instructions(win: Window, keyboard: Keyboard):
    """Instruction routine."""
    text = TextStim(
        win=win,
        text="You will hear 15 pure tones followed by an instrument sound.\n"
        "After the instrument sound, enter the instrument category on the "
        "keyboard.",
        height=0.05,
        pos=(0, 0.5),
    )
    images = load_instrument_images()
    percussion_image = ImageStim(win, images["percussion"], pos=(-0.5, -0.2))
    string_image = ImageStim(win, images["string"], pos=(0, -0.2))
    wind_image = ImageStim(win, images["wind"], pos=(+0.5, -0.2))
    percussion_text = TextStim(
        win=win,
        text="Press 1 for percussion",
        height=0.05,
        pos=(-0.5, 0.15),
    )
    string_text = TextStim(
        win=win,
        text="Press 2 for string",
        height=0.05,
        pos=(0, 0.15),
    )
    wind_text = TextStim(
        win=win,
        text="Press 3 for wind",
        height=0.05,
        pos=(0.5, 0.15),
    )
    continue_text = TextStim(
        win=win,
        text="Press SPACE to continue.",
        height=0.05,
        pos=(0, -0.65),
    )
    text.setAutoDraw(True)
    percussion_image.setAutoDraw(True)
    string_image.setAutoDraw(True)
    wind_image.setAutoDraw(True)
    percussion_text.setAutoDraw(True)
    string_text.setAutoDraw(True)
    wind_text.setAutoDraw(True)
    continue_text.setAutoDraw(True)
    win.flip()
    while True:  # wait for 'space'
        keys = keyboard.getKeys(keyList=["space"], waitRelease=False)
        if len(keys) != 0:
            break
        win.flip()
    text.setAutoDraw(False)
    percussion_image.setAutoDraw(False)
    string_image.setAutoDraw(False)
    wind_image.setAutoDraw(False)
    percussion_text.setAutoDraw(False)
    string_text.setAutoDraw(False)
    wind_text.setAutoDraw(False)
    continue_text.setAutoDraw(False)


def _pause(win: Window, keyboard: Keyboard):
    """Pause routine."""
    text = TextStim(
        win=win,
        text="Pause.\nPress SPACE to continue.",
        height=0.05,
        pos=(0, 0),
    )
    text.setAutoDraw(True)
    win.flip()
    while True:  # wait for 'space'
        keys = keyboard.getKeys(keyList=["space"], waitRelease=False)
        if len(keys) != 0:
            break
        win.flip()
    text.setAutoDraw(False)


def _fixation_cross(
    win: Window,
    task: Callable,
    args: tuple,
    condition_name: str,
) -> Union[None, NDArray[float]]:
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
    result = task(*args)
    cross.setAutoDraw(False)
    return result


def _prepare_category(
    win: Window,
) -> Tuple[Tuple[ImageStim, ...], Tuple[TextStim, ...]]:
    """Prepare components for category routine."""
    images = load_instrument_images()
    percussion_image = ImageStim(win, images["percussion"], pos=(-0.5, -0.2))
    string_image = ImageStim(win, images["string"], pos=(0, -0.2))
    wind_image = ImageStim(win, images["wind"], pos=(+0.5, -0.2))
    images = (percussion_image, string_image, wind_image)
    percussion_text = TextStim(
        win=win,
        text="Press 1 for percussion",
        height=0.05,
        pos=(-0.5, 0.15),
    )
    string_text = TextStim(
        win=win,
        text="Press 2 for string",
        height=0.05,
        pos=(0, 0.15),
    )
    wind_text = TextStim(
        win=win,
        text="Press 3 for wind",
        height=0.05,
        pos=(0.5, 0.15),
    )
    texts = (percussion_text, string_text, wind_text)
    return images, texts


def _category(
    win: Window,
    trigger: Union[MockTrigger, ParallelPortTrigger],
    tdef: TriggerDef,
    keyboard: Keyboard,
    images_category: Tuple[ImageStim, ...],
    texts_category: Tuple[ImageStim, ...],
) -> int:
    """Category routine."""
    for text in texts_category:
        text.setAutoDraw(True)
    for img in images_category:
        img.setAutoDraw(True)
    win.flip()
    while True:  # wait for '1', '2', '3'
        keys = keyboard.getKeys(keyList=["1", "2", "3"], waitRelease=False)
        if len(keys) != 0:
            logger.debug("Key pressed: %s", [key.name for key in keys])
            trigger.signal(tdef.by_name[keys[-1].name])
            break
    for text in texts_category:
        text.setAutoDraw(False)
    for img in images_category:
        img.setAutoDraw(False)
    return int(keys[-1].name)


def _confidence(win: Window) -> float:
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
    confidence = slider.markerPos
    text.setAutoDraw(False)
    slider.setAutoDraw(False)
    button.setAutoDraw(False)
    return confidence

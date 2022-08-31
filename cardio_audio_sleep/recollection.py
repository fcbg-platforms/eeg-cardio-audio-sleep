from itertools import chain
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from bsl.triggers import LSLTrigger
from numpy.random import default_rng
from numpy.typing import NDArray
from psychopy.clock import Clock
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
from .config import load_config
from .tasks import asynchronous, isochronous, synchronous
from .utils import (
    generate_async_timings_based_on_mean,
    generate_sequence,
    load_instrument_categories,
    load_instrument_images,
)


def recollection(
    win: Window,
    args_mapping: dict,
    trigger_instrument: LSLTrigger,
    instrument_files_example: dict,
    instrument_files_sleep: dict,
    instrument_files_recollection: dict,
    dev: bool,
):
    """Recollection task."""
    # prepare keyboard for interaction
    keyboard = Keyboard()
    win.callOnFlip(keyboard.clearEvents, eventType="keyboard")
    keyboard.stop()
    keyboard.clearEvents()
    # prepare components displayed most of the time
    images = _prepare_components(win)

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
    args_mapping, config = _load_config(args_mapping, dev)
    # variable to store the timings from the synchronous condition
    sequence_timings = None
    # variable to store the responses
    responses = dict(condition=[], instrument=[], confidence=[])
    # prepare the random distribution of number of stimuli
    stimuli_distribution = _prepare_distribution_stimuli(
        recollection_tests,
        config,
    )
    condition_counters = {
        "synchronous": 0,
        "isochronous": 0,
        "asynchronous": 0,
    }

    # run routines
    n_pause = 6 if dev else 24
    try:
        _instructions(win, keyboard)
        trigger_instrument.signal("recollection-examples")
        _training(
            win,
            images,
            keyboard,
            instrument_files_example,
            args_mapping["isochronous"],
            trigger_instrument,
        )
        trigger_instrument.signal("recollection")
        for k, (condition, instrument) in enumerate(recollection_tests):
            if k != 0 and k % n_pause == 0:
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
            n_stimuli = stimuli_distribution[condition][
                condition_counters[condition]
            ]
            args[2] = generate_sequence(
                n_stimuli,
                config[condition]["n_omissions"],
                config[condition]["edge_perc"],
                args[1],  # tdef
            )
            logger.debug(
                "Number of stimuli set to %i for %s block.",
                n_stimuli,
                condition,
            )
            condition_counters[condition] += 1
            if condition == "isochronous":
                assert sequence_timings is not None
                args[3] = np.median(np.diff(sequence_timings))
                logger.info("Delay for isochronous: %.2f (s).", args[3])
            if condition == "asynchronous":
                timings = generate_async_timings_based_on_mean(
                    sequence_timings, n=n_stimuli
                )
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

            result = _task_routine(
                win,
                task_mapping[condition],
                tuple(args),
                images,
            )
            _category(images)
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
) -> List[Tuple[str, Path]]:
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


def _prepare_distribution_stimuli(
    recollection_tests: List[Tuple[str, Path]],
    config: dict,
    delta: float = 2,
) -> Dict[str, List[int]]:
    """Prepare the randomize distribution of stimuli for each condition."""
    # count the number of tests in each condition
    number_tests = dict()
    number_tests["synchronous"] = len(
        [elt for elt in recollection_tests if elt[0] == "synchronous"]
    )
    number_tests["isochronous"] = len(
        [elt for elt in recollection_tests if elt[0] == "isochronous"]
    )
    number_tests["asynchronous"] = len(
        [elt for elt in recollection_tests if elt[0] == "asynchronous"]
    )
    # draw samples from a normal distribution
    rng = default_rng()
    distribution = dict()
    for condition in ("synchronous", "isochronous", "asynchronous"):
        n_stimuli = config[condition]["n_stimuli"]
        distribution[condition] = rng.integers(
            n_stimuli - delta,
            n_stimuli + delta,
            number_tests[condition],
            endpoint=True,
        )
    logger.debug(
        "[Recollection] The distribution of stimuli has been set to:\n"
        "\t Synchronous: %s\n"
        "\t Isochronous: %s\n"
        "\t Asynchronous: %s\n",
        tuple(distribution["synchronous"]),
        tuple(distribution["isochronous"]),
        tuple(distribution["asynchronous"]),
    )

    return distribution


def _load_config(args_mapping: dict, dev: bool) -> Tuple[dict, dict]:
    """Load config and prepare arguments."""
    # load config
    config, _ = load_config("config-recollection.ini", dev)
    assert config["synchronous"]["instrument"]
    assert config["isochronous"]["instrument"]
    assert config["asynchronous"]["instrument"]
    args_mapping["synchronous"][10] = config["synchronous"]["n_instrument"]
    args_mapping["isochronous"][6] = config["isochronous"]["n_instrument"]
    args_mapping["asynchronous"][6] = config["asynchronous"]["n_instrument"]
    return args_mapping, config


def _prepare_components(
    win: Window,
) -> Tuple[Union[ImageStim, ShapeStim], ...]:
    """Prepare most used components."""
    instrument_images = load_instrument_images()
    instruments = load_instrument_categories()
    assert sorted(instrument_images.keys()) == instruments  # sanity-check
    # determine positions
    positions = np.linspace(-0.5, 0.5, len(instruments))
    # create images
    images = list()
    for instrument, position in zip(instruments, positions):
        images.append(
            ImageStim(win, instrument_images[instrument], pos=(position, -0.5))
        )
    # add fixation cross
    cross = ShapeStim(
        win=win,
        vertices="cross",
        units="height",
        size=(0.05, 0.05),
        lineColor="white",
        fillColor="white",
    )
    images.append(cross)
    return tuple(images)


def _instructions(win: Window, keyboard: Keyboard):
    """Instruction routine."""
    instrument_images = load_instrument_images()
    instruments = load_instrument_categories()
    assert sorted(instrument_images.keys()) == instruments  # sanity-check
    # determine positions
    positions = np.linspace(-0.5, 0.5, len(instruments))
    # create images/texts
    images = list()
    texts = list()
    for k, (instrument, position) in enumerate(zip(instruments, positions)):
        images.append(
            ImageStim(win, instrument_images[instrument], pos=(position, -0.2))
        )
        texts.append(
            TextStim(
                win=win,
                text=f"Press {k+1} for {instrument}",
                height=0.05,
                pos=(position, 0.15),
            )
        )
    # create instructions/continue text
    instruction_text = TextStim(
        win=win,
        text="You will hear pure tones followed by an instrument sound.\n"
        "After the instrument sound, enter the instrument category on "
        "the triggerbox in front of you.\n\n"
        "You should respond as fast as possible, even if the instrument sound "
        "is still playing.",
        height=0.05,
        pos=(0, 0.5),
    )
    continue_text = TextStim(
        win=win,
        text="Press SPACE for 2 examples.",
        height=0.05,
        pos=(0, -0.65),
    )
    # display
    for img, txt in zip(images, texts):
        img.setAutoDraw(True)
        txt.setAutoDraw(True)
    instruction_text.setAutoDraw(True)
    continue_text.setAutoDraw(True)
    win.flip()

    keyboard.start()
    while True:  # wait for 'space'
        keys = keyboard.getKeys(keyList=["space"], waitRelease=False)
        if len(keys) != 0:
            break
        win.flip()
    keyboard.stop()
    keyboard.clearEvents()

    # remove
    for img, txt in zip(images, texts):
        img.setAutoDraw(False)
        txt.setAutoDraw(False)
    instruction_text.setAutoDraw(False)
    continue_text.setAutoDraw(False)


def _training(
    win,
    images,
    keyboard,
    instrument_files_example,
    args_iso,
    trigger_instrument,
):
    """Example routine following the instructions."""
    n_examples = 6
    instruments = list(chain(*instrument_files_example.values())) * 2
    for k in range(n_examples):  # number of examples
        idx = np.random.randint(0, len(instruments))
        instrument = instruments[idx]
        del instruments[idx]
        logger.info(
            "[Recollection- Training] %i / %i : %s sound.",
            k + 1,
            n_examples,
            instrument.name,
        )

        # generate stimuli sequence
        n_stimuli = 2
        args_iso[2] = generate_sequence(
            n_stimuli,
            0,
            0,
            args_iso[1],  # tdef
        )
        logger.debug("Number of stimuli set to %i.", n_stimuli)
        # set iso inter-stimuli delay
        args_iso[3] = 0.75
        # set instrument
        args_iso[5] = instrument
        trigger_instrument.signal(instrument.name)

        # run task
        _task_routine(
            win,
            isochronous,
            tuple(args_iso),
            images,
        )
        _category(images)

    continue_text = TextStim(
        win=win,
        text="Press SPACE to start the task.",
        height=0.05,
        pos=(0, 0),
    )
    continue_text.setAutoDraw(True)
    win.flip()

    keyboard.start()
    while True:  # wait for 'space'
        keys = keyboard.getKeys(keyList=["space"], waitRelease=False)
        if len(keys) != 0:
            break
        win.flip()
    keyboard.stop()
    keyboard.clearEvents()
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
    keyboard.start()
    while True:  # wait for 'space'
        keys = keyboard.getKeys(keyList=["space"], waitRelease=False)
        if len(keys) != 0:
            break
        win.flip()
    keyboard.stop()
    keyboard.clearEvents()
    text.setAutoDraw(False)


def _task_routine(
    win: Window,
    task: Callable,
    args: tuple,
    images: Tuple[Union[ImageStim, ShapeStim], ...],
) -> Optional[NDArray[float]]:
    """Fixation cross routine."""
    for img in images:
        img.setAutoDraw(True)
    win.flip()
    result = task(*args)
    return result


def _category(images: Tuple[Union[ImageStim, ShapeStim], ...]) -> None:
    """Category routine."""
    timer = Clock()
    while True:
        if 3 < timer.getTime():
            break
    for img in images:
        img.setAutoDraw(False)


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

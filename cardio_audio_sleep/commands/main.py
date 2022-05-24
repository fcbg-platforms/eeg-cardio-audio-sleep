import argparse
import time

try:
    from importlib.resources import files  # type: ignore
except ImportError:
    from importlib_resources import files  # type: ignore

from bsl.triggers import ParallelPortTrigger
from bsl.utils.lsl import list_lsl_streams
from psychopy.visual import ImageStim
from PyQt5.QtWidgets import QApplication

from .. import logger, peak_detection_parameters_tuning, set_log_level
from ..config import load_triggers
from ..eye_link import Eyelink
from ..utils import search_ANT_amplifier
from .cli import input_ecg_ch_name
from .gui import GUI


def cas():
    """Entrypoint for cas <command> usage."""
    parser = argparse.ArgumentParser(
        prog="CAS", description="Cardio-Audio-Sleep GUI"
    )
    parser.add_argument(
        "--ecg",
        help="name of the ECG channel",
        type=str,
        metavar=str
    )
    parser.add_argument(
        "--eye_tracker", help="enable eye-tracking", action="store_true"
    )
    parser.add_argument(
        "--verbose", help="enable debug logs", action="store_true"
    )
    args = parser.parse_args()
    set_log_level("DEBUG" if args.verbose else "INFO")

    # setup eye-tracker
    if args.eye_tracker:
        eye_link = Eyelink(fname="TEST")
        eye_link.calibrate_el()
        eye_link.start_recording_el()

        # draw a fixation cross
        cross_path = str(
            files("cardio_audio_sleep.visuals").joinpath("fixation.png")
        )
        cross = ImageStim(win=eye_link.win, image=cross_path)
        cross.autoDraw = False
        cross.draw()
        eye_link.win.flip()
    else:
        eye_link = None

    # ask for ECG channel name if it's not provided as argument
    ecg_ch_name = input_ecg_ch_name() if args.ecg is None else args.ecg

    app = QApplication([])
    window = GUI(ecg_ch_name, eye_link)
    window.show()
    app.exec()


def pds():
    """Entrypoint for pds <command> usage."""
    parser = argparse.ArgumentParser(
        prog="CAS - PDS", description="Peak detection settings."
    )
    parser.add_argument(
        "--ecg_ch_name",
        type=str,
        metavar="str",
        help="Name of the ECG channel.",
        default=None,
    )
    parser.add_argument(
        "--stream_name",
        type=str,
        metavar="str",
        help="Name of the LSL stream.",
        default=None,
    )
    parser.add_argument(
        "--duration_buffer",
        type=int,
        metavar="int",
        help="Duration of the detector's buffer in seconds.",
        default=4,
    )
    args = parser.parse_args()
    if args.ecg_ch_name is None:
        ecg_ch_name = input_ecg_ch_name()
    else:
        ecg_ch_name = args.ecg_ch_name
    height, prominence, width = peak_detection_parameters_tuning(
        ecg_ch_name, args.stream_name, args.duration_buffer
    )

    # format output
    print("-----------------------------------------")
    print("The peak detection settings selected are:")
    print(f"Height       ->  {height}")
    print(f"Prominence   ->  {prominence}")
    print(f"Width:       ->  {width}")
    print("-----------------------------------------")


def test():
    """Run test on the LSL stream and triggers."""
    error = False
    # look for the LSL stream
    logger.info("Looking for ANT LSL stream..")
    try:
        stream_name = search_ANT_amplifier()
        logger.info("ANT LSL stream found!")
    except RuntimeError:
        error = True
        logger.error(
            "ANT LSL stream could not be found. Is the amplifier "
            "correctly connected and the LSL app started?"
        )

    # check the sampling rate
    stream_names, stream_infos = list_lsl_streams(ignore_markers=True)
    idx = stream_names.index(stream_name)
    sinfo = stream_infos[idx]
    if sinfo.nominal_srate() == 1024:
        logger.info(
            "ANT LSL stream sampling rate is correctly set at 1024 Hz."
        )
    else:
        error = True
        logger.error(
            "ANT LSL stream sampling rate is not correctly set! "
            "Currently %s Hz, while 1024 Hz is expected!",
            sinfo.nominal_srate(),
        )

    # check the trigger
    try:
        trigger = ParallelPortTrigger("/dev/parport0")
    except Exception:
        error = True
        logger.error(
            "Could not initialize the parallel port trigger. Is the LPT cable "
            "correctly connected and does '/dev/parport0' exist?"
        )

    if error:
        logger.info(
            "Something went wrong.. please check the setup! "
            "Aborting further tests.."
        )
        return None

    # check the trigger pins
    logger.info(
        "Testing all the triggers. Please look at a StreamViewer and "
        "confirm that each value is correctly displayed."
    )
    tdef = load_triggers()
    for value in tdef.by_value:
        logger.info("Testing trigger %i..", value)
        trigger.signal(value)
        time.sleep(0.5)

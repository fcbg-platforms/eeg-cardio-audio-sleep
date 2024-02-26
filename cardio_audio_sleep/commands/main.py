import argparse
import os
import time
from datetime import datetime
from pathlib import Path

from bsl.utils.lsl import list_lsl_streams
from byte_triggers import ParallelPortTrigger
from PyQt5.QtWidgets import QApplication

from .. import logger, peak_detection_parameters_tuning, set_log_level
from ..config import load_triggers
from ..utils import search_amplifier
from .cli import input_ecg_ch_name
from .gui import GUI


def cas():
    """Entrypoint for cas <command> usage."""
    parser = argparse.ArgumentParser(prog="CAS", description="Cardio-Audio-Sleep GUI")
    parser.add_argument("--ecg", help="name of the ECG channel", type=str, metavar=str)
    parser.add_argument(
        "--eye_tracker", help="enable eye-tracking", action="store_true"
    )
    parser.add_argument(
        "--instrument", help="enable instrument sounds", action="store_true"
    )
    parser.add_argument(
        "--dev", help="load short sequence for testing", action="store_true"
    )
    parser.add_argument("--verbose", help="enable debug logs", action="store_true")
    args = parser.parse_args()
    set_log_level("DEBUG" if args.verbose else "INFO")

    # setup eye-tracker
    if args.eye_tracker:
        from ..eye_link import Eyelink, EyelinkMock

        if isinstance(Eyelink, EyelinkMock):
            raise ImportError(
                "Eyetracker requires 'pylink' on all platforms and 'wxPython' on Linux."
            )

        directory = str(Path().home() / "cardio-audio-sleep-eye-tracker")
        os.makedirs(directory, exist_ok=True)
        fname = datetime.now().strftime("%m%dh%I")
        eye_link = Eyelink(directory, fname)
    else:
        from ..eye_link import EyelinkMock

        eye_link = EyelinkMock()

    # ask for ECG channel name if it's not provided as argument
    ecg_ch_name = input_ecg_ch_name() if args.ecg is None else args.ecg

    app = QApplication([])
    window = GUI(ecg_ch_name, eye_link, args.instrument, args.dev)
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
    parser = argparse.ArgumentParser(prog="CAS - Test", description="Test CAS system.")
    parser.add_argument(
        "--amplifier",
        type=str,
        metavar="str",
        help="Either 'ant' or 'micromed'.",
        default="micromed",
    )
    args = parser.parse_args()

    # look for the LSL stream
    logger.info("Looking for LSL stream..")
    try:
        stream_name = search_amplifier(args.amplifier)
        logger.info("LSL stream found!")
    except RuntimeError:
        logger.error(
            "LSL stream could not be found. Is the amplifier "
            "correctly connected and the LSL app started? "
            "Aborting further tests.."
        )
        return None

    # check the sampling rate
    stream_names, stream_infos = list_lsl_streams(ignore_markers=True)
    idx = stream_names.index(stream_name)
    sinfo = stream_infos[idx]
    if sinfo.nominal_srate() == 1024:
        logger.info("ANT LSL stream sampling rate is correctly set at 1024 Hz.")
    else:
        logger.error(
            "ANT LSL stream sampling rate is not correctly set! "
            "Currently %s Hz, while 1024 Hz is expected! "
            "Aborting further tests..",
            sinfo.nominal_srate(),
        )
        return None

    # check the trigger
    triggers = dict()
    try:
        trigger = ParallelPortTrigger("/dev/parport0", delay=5)
        triggers["lpt"] = trigger
    except Exception:
        pass
    try:
        trigger = ParallelPortTrigger("arduino", delay=5)
        triggers["arduino"] = trigger
    except Exception:
        pass

    if len(triggers) == 2:
        logger.error(
            "Found both a LPT port on '/dev/parport0' and an arduino to LPT converter. "
            "Please use the on-board LPT port instead of a converter and set 'lpt' in "
            "the configuration. Aborting further tests.."
        )
        return None
    elif len(triggers) == 0:
        logger.error(
            "Could not find a parallel port or an arduino to parallel port converter. "
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
        time.sleep(1)

    # clean-up
    del trigger

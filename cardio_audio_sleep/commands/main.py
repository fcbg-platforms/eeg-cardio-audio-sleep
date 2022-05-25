import argparse

from PyQt5.QtWidgets import QApplication

from .. import peak_detection_parameters_tuning, set_log_level
from ..eye_link import Eyelink, EyelinkMock
from .cli import input_ecg_ch_name
from .gui import GUI


def cas():
    """Entrypoint for cas <command> usage."""
    parser = argparse.ArgumentParser(
        prog="CAS", description="Cardio-Audio-Sleep GUI"
    )
    parser.add_argument(
        "--ecg", help="name of the ECG channel", type=str, metavar=str
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
        eye_link = Eyelink("./", "TEST")
    else:
        eye_link = EyelinkMock()

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

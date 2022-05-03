import argparse

from PyQt5.QtWidgets import QApplication

from .. import peak_detection_parameters_tuning
from .cli import (
    input_ecg_ch_name,
    input_peak_height_perc,
    input_peak_prominence,
    input_peak_width,
)
from .gui import GUI


def cas():
    """Entrypoint for cas <command> usage."""
    ecg_ch_name = input_ecg_ch_name()
    peak_height_perc = input_peak_height_perc()
    peak_prominence = input_peak_prominence()
    peak_width = input_peak_width()

    app = QApplication([])
    window = GUI(ecg_ch_name, peak_height_perc, peak_prominence, peak_width)
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

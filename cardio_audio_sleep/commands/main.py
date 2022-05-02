from PyQt5.QtWidgets import QApplication

from .cli import (
    input_ecg_ch_name,
    input_peak_height_perc,
    input_peak_prominence,
    input_peak_width,
)
from .gui import GUI


def run():
    """Entrypoint for cas <command> usage."""
    ecg_ch_name = input_ecg_ch_name()
    peak_height_perc = input_peak_height_perc()
    peak_prominence = input_peak_prominence()
    peak_width = input_peak_width()

    app = QApplication([])
    window = GUI(ecg_ch_name, peak_height_perc, peak_prominence, peak_width)
    window.show()
    app.exec()

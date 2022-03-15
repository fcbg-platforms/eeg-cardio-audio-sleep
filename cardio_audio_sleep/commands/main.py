from PyQt5.QtWidgets import QApplication

from .gui import GUI


def run():
    """Entrypoint for cas <command> usage."""
    ecg_ch_name = 'AUX7'
    peak_height_perc = 90
    peak_prominence = 500
    peak_width = None

    app = QApplication([])
    window = GUI(ecg_ch_name, peak_height_perc, peak_prominence,
                 peak_width)
    window.show()
    app.exec()

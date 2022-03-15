from PyQt5.QtWidgets import QApplication

from .gui import GUI


def run():
    """Entrypoint for cas <command> usage."""
    app = QApplication([])
    window = GUI()
    window.show()
    app.exec()

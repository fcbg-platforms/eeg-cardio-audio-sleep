from PyQt5.QtCore import QSize, Qt, QRect
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QWidget, QMainWindow, QPushButton, QLabel

from .. import logger


class GUI(QMainWindow):
    """Application window and layout."""

    def __init__(self):
        super().__init__()
        self.load_ui()
        self.connect_signals_to_slots()

    # -------------------------------------------------------------------------
    def load_ui(self):
        # Main window
        self.setWindowTitle('Cardio-Audio-Sleep experiment')
        self.setFixedSize(QSize(800, 200))
        self.setContextMenuPolicy(Qt.NoContextMenu)

        # Main widget
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("central_widget")

        # Add blocks
        self.blocks = list()
        for k in range(5):
            block = Block(self.central_widget, '')
            block.setGeometry(QRect(50 + 145 * k, 20, 120, 80))
            block.setAlignment(Qt.AlignCenter)
            block.setObjectName(f"block{k+1}")
            self.blocks.append(block)

        # Add labels
        past = QLabel(self.central_widget)
        past.setGeometry(QRect(50, 115, 265, 20))
        past.setAlignment(Qt.AlignCenter)
        past.setObjectName("past")
        past.setText("Past")

        future = QLabel(self.central_widget)
        future.setGeometry(QRect(485, 115, 265, 20))
        future.setAlignment(Qt.AlignCenter)
        future.setObjectName("future")
        future.setText("Future")

        current = QLabel(self.central_widget)
        current.setGeometry(QRect(340, 115, 120, 20))
        current.setAlignment(Qt.AlignCenter)
        current.setObjectName("current")
        current.setText("Current")

        # Add push buttons
        self.pushButton_start = QPushButton(self.central_widget)
        self.pushButton_start.setEnabled(True)
        self.pushButton_start.setGeometry(QRect(25, 150, 240, 32))
        self.pushButton_start.setObjectName("pushButton_start")
        self.pushButton_start.setText("Start/Resume")

        self.pushButton_pause = QPushButton(self.central_widget)
        self.pushButton_pause.setEnabled(False)
        self.pushButton_pause.setGeometry(QRect(280, 150, 240, 32))
        self.pushButton_pause.setObjectName("pushButton_pause")
        self.pushButton_pause.setText("Pause")

        self.pushButton_stop = QPushButton(self.central_widget)
        self.pushButton_stop.setEnabled(False)
        self.pushButton_stop.setGeometry(QRect(535, 150, 240, 32))
        self.pushButton_stop.setObjectName("pushButton_stop")
        self.pushButton_stop.setText("Stop")

        # Set central widget
        self.setCentralWidget(self.central_widget)

        logger.debug('UI loaded.')

    # -------------------------------------------------------------------------
    def connect_signals_to_slots(self):
        self.pushButton_start.clicked.connect(self.pushButton_start_clicked)
        self.pushButton_pause.clicked.connect(self.pushButton_pause_clicked)
        self.pushButton_stop.clicked.connect(self.pushButton_stop_clicked)

    def pushButton_start_clicked(self):
        logger.debug('Start requested.')
        self.pushButton_start.setEnabled(False)
        self.pushButton_pause.setEnabled(True)
        self.pushButton_stop.setEnabled(True)

    def pushButton_pause_clicked(self):
        logger.debug('Pause requested.')
        self.pushButton_start.setEnabled(True)
        self.pushButton_pause.setEnabled(False)
        self.pushButton_stop.setEnabled(True)

    def pushButton_stop_clicked(self):
        logger.debug('Stop requested.')
        self.pushButton_start.setEnabled(False)
        self.pushButton_pause.setEnabled(False)
        self.pushButton_stop.setEnabled(False)


class Block(QLabel):
    """
    Widget to represent a block (Baseline, Synchronous, Isochronous or
    Asynchronous).

    Parameters
    ----------
    parent : QWidget
        Parent widget.
    btype : str
        Type: 'baseline', 'synchronous', 'isochronous' or 'asynchronous'.
    """

    colors = {
        'baseline': 'green',
        'synchronous': 'blue',
        'isochronous': 'red',
        'asynchronous': 'grey',
        '': 'white'}

    def __init__(self, parent, btype):
        super().__init__(parent)
        assert btype in self.colors  # sanity-check
        self._btype = btype

        # Set text/font/alignment
        self.setText(self._btype)
        self.setFont(QFont("Arial", 18))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(self.colors[self._btype]))
        self.setPalette(palette)

    @property
    def btype(self):
        return self._btype

    @btype.setter
    def btype(self, btype):
        assert btype in self.colors  # sanity-check
        self._btype = btype
        # Set text
        self.setText(self._btype)
        # Set background color
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(self.colors[self._btype]))
        self.setPalette(palette)

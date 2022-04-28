import multiprocessing as mp
from typing import Optional

from bsl.triggers import ParallelPortTrigger
import numpy as np
import psutil
from PyQt5.QtCore import QSize, Qt, QRect, pyqtSlot, QTimer
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QWidget, QMainWindow, QPushButton, QLabel

from .. import logger
from ..config import load_triggers, load_config
from ..tasks import (baseline, synchronous, isochronous, asynchronous,
                     inter_block)
from ..utils import (generate_blocks_sequence, generate_sequence,
                     generate_async_timings, search_ANT_amplifier)


class GUI(QMainWindow):
    """Application window and layout.

    Parameters
    ----------
    ecg_ch_name : str
        Name of the ECG channel.
    peak_height_perc : float
        Minimum height of the peak expressed as a percentile of the samples in
        the buffer.
    peak_prominence : float | None
        Minimum peak prominence as defined by scipy.
    peak_width : float | None
        Minimum peak width expressed in ms. Default to None.
    """

    def __init__(
            self,
            ecg_ch_name: str,
            peak_height_perc: float,
            peak_prominence: Optional[float],
            peak_width: Optional[float],
            ):
        super().__init__()

        # define mp Queue
        self.queue = mp.Queue()

        # load configuration
        self.load_config(
            ecg_ch_name,
            peak_height_perc,
            peak_prominence,
            peak_width,
            )

        # load GUI
        self.load_ui()
        self.connect_signals_to_slots()

        # block generation
        self.all_blocks = list()
        for k in range(3):
            block = generate_blocks_sequence(self.all_blocks)
            self.all_blocks.append(block)
            self.blocks[k+2].btype = block

        # placeholder for the last valid sequence for async blocks
        self.last_valid_timings = None

        # define Qt Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def load_config(
            self,
            ecg_ch_name: str,
            peak_height_perc: float,
            peak_prominence: Optional[float],
            peak_width: Optional[float],
            ):
        self.config = load_config()
        self.tdef = load_triggers()
        self.trigger = ParallelPortTrigger('/dev/parport0')
        stream_name = search_ANT_amplifier()

        # Create task mapping
        self.task_mapping = {
            'baseline': baseline,
            'synchronous': synchronous,
            'isochronous': isochronous,
            'asynchronous': asynchronous
            }

        # Create args
        self.args_mapping = {
            'baseline': (self.trigger, self.tdef,
                         self.config['baseline']['duration']),
            'synchronous': (self.trigger, self.tdef, None, stream_name,
                            ecg_ch_name, peak_height_perc, peak_prominence,
                            peak_width, self.queue),
            'isochronous': (self.trigger, self.tdef, None, None),
            'asynchronous': (self.trigger, self.tdef, None, None),
            }

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
            block.setObjectName(f"block{k}")
            if k in (0, 1):  # disable block 0 and 1 (past)
                block.setEnabled(False)
            self.blocks.append(block)

        # Add labels
        past = QLabel(self.central_widget)
        past.setGeometry(QRect(50, 115, 265, 20))
        past.setAlignment(Qt.AlignCenter)
        past.setObjectName("past")
        past.setText("Previous blocks")

        future = QLabel(self.central_widget)
        future.setGeometry(QRect(485, 115, 265, 20))
        future.setAlignment(Qt.AlignCenter)
        future.setObjectName("future")
        future.setText("Next blocks")

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
        self.pushButton_start.setText("Start")

        self.pushButton_pause = QPushButton(self.central_widget)
        self.pushButton_pause.setEnabled(False)
        self.pushButton_pause.setGeometry(QRect(280, 150, 240, 32))
        self.pushButton_pause.setObjectName("pushButton_pause")
        self.pushButton_pause.setText("Pause")
        self.pushButton_pause.setCheckable(True)

        self.pushButton_stop = QPushButton(self.central_widget)
        self.pushButton_stop.setEnabled(False)
        self.pushButton_stop.setGeometry(QRect(535, 150, 240, 32))
        self.pushButton_stop.setObjectName("pushButton_stop")
        self.pushButton_stop.setText("Stop")

        # Set central widget
        self.setCentralWidget(self.central_widget)

        logger.debug('UI loaded.')

    # -------------------------------------------------------------------------
    def update(self):
        """Update loop called every timer tick checking if the task is still
        on going or if we can schedule the next block."""
        self.process.join(timeout=0.2)  # blocks 0.2 second
        if not self.process.is_alive():
            if self.process_block_name == 'synchronous':
                self.sequence_timings = self.queue.get()
            if self.process_block_name == 'inter-block':
                self.start_new_block()
            else:
                self.start_inter_block()

    def start_new_block(self, first: bool = False):
        """Starts a new block. If this is the first block run, initialization
        correctly placed the initial 3 blocks. Else, we start by rolling the
        blocks. Arguments must be determined depending on the block played."""
        if not first:  # roll blocks
            for k, block in enumerate(self.blocks):
                if k == len(self.blocks) - 1:
                    block.btype = generate_blocks_sequence(self.all_blocks)
                    self.all_blocks.append(block.btype)
                else:
                    block.btype = self.blocks[k+1].btype

        # determine arguments
        btype = self.blocks[2].btype
        if btype == 'baseline':
            args = self.args_mapping[btype]
        else:
            args = list(self.args_mapping[btype])
            args[2] = generate_sequence(
                self.config[btype]['n_stimuli'],
                self.config[btype]['n_omissions'],
                self.config[btype]['edge_perc'],
                self.tdef)

            if btype == 'isochronous':
                args[3] = np.median(np.diff(self.sequence_timings))
                logger.info('Delay for isochronous: %.2f (s).', args[3])
            if btype == 'asynchronous':
                timings, valid = generate_async_timings(self.sequence_timings)
                if valid:
                    self.last_valid_timings = timings
                    args[3] = timings
                elif not valid and self.last_valid_timings is None:
                    args[3] = timings
                else:
                    np.random.shuffle(self.last_valid_timings)
                    args[3] = self.last_valid_timings
                logger.info('Average delay for asynchronous: %.2f (s).',
                            np.median(np.diff(args[3])))

        # start new process
        self.process = mp.Process(
            target=self.task_mapping[self.blocks[2].btype], args=tuple(args))
        self.process.start()
        self.psutil_process = psutil.Process(self.process.pid)
        self.process_block_name = btype

    def start_inter_block(self):
        """Start an inter-block process that waits for a fix duration."""
        self.process = mp.Process(
            target=inter_block,
            args=(self.config['block']['inter_block'], True))
        self.process.start()
        self.psutil_process = psutil.Process(self.process.pid)
        self.process_block_name = 'inter-block'

    # -------------------------------------------------------------------------
    def connect_signals_to_slots(self):
        self.pushButton_start.clicked.connect(self.pushButton_start_clicked)
        self.pushButton_pause.clicked.connect(self.pushButton_pause_clicked)
        self.pushButton_stop.clicked.connect(self.pushButton_stop_clicked)

    @pyqtSlot()
    def pushButton_start_clicked(self):
        logger.debug('Start requested.')
        self.pushButton_start.setEnabled(False)
        self.pushButton_pause.setEnabled(True)
        self.pushButton_stop.setEnabled(True)

        # Launch first block
        self.start_new_block(first=True)

        # Start timer
        self.timer.start(2000)

    @pyqtSlot()
    def pushButton_pause_clicked(self):
        self.pushButton_start.setEnabled(False)
        self.pushButton_pause.setEnabled(True)
        self.pushButton_stop.setEnabled(True)

        # change text on button
        if self.pushButton_pause.isChecked():
            logger.debug('Pause requested.')
            self.pushButton_pause.setText("Resume")
            self.timer.stop()
            try:
                self.psutil_process.suspend()
            except psutil.NoSuchProcess:
                logger.warning('No process found to suspend.')
            self.trigger.signal(self.tdef.pause)
        else:
            logger.debug('Resume requested.')
            self.pushButton_pause.setText("Pause")
            self.timer.start(2000)
            try:
                self.psutil_process.resume()
            except psutil.NoSuchProcess:
                logger.warning('No process found to resume.')
            self.trigger.signal(self.tdef.resume)

    @pyqtSlot()
    def pushButton_stop_clicked(self):
        logger.debug('Stop requested.')
        self.pushButton_start.setEnabled(False)
        self.pushButton_pause.setEnabled(False)
        self.pushButton_stop.setEnabled(False)
        self.timer.stop()
        self.process.join(1)
        if self.process.is_alive():
            self.process.kill()


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
        '': None,
        }

    def __init__(self, parent: QWidget, btype: str):
        super().__init__(parent)
        assert btype in self.colors  # sanity-check
        self._btype = btype

        # Set text/font/alignment
        self.setText(self._btype)
        self.setFont(QFont("Arial", 14))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set background color
        self.setAutoFillBackground(True)
        if self.colors[self._btype] is not None:
            palette = self.palette()
            palette.setColor(QPalette.Window, QColor(self.colors[self._btype]))
            self.setPalette(palette)

    @property
    def btype(self):
        return self._btype

    @btype.setter
    def btype(self, btype: str):
        assert btype in self.colors  # sanity-check
        self._btype = btype
        # Set text
        self.setText(self._btype)
        # Set background color
        if self.colors[self._btype] is not None:
            palette = self.palette()
            palette.setColor(QPalette.Window, QColor(self.colors[self._btype]))
            self.setPalette(palette)

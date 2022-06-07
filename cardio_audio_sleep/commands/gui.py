import multiprocessing as mp
import sys
from typing import Optional

import numpy as np
import psutil
from bsl.triggers import MockTrigger, ParallelPortTrigger
from psychopy.monitors import Monitor
from psychopy.visual import TextStim, Window
from PyQt5.QtCore import QRect, QSize, Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import (
    QDial,
    QDoubleSpinBox,
    QFrame,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from .. import logger
from .._typing import EYELink
from ..config import load_config, load_triggers
from ..eye_link import EyelinkMock
from ..tasks import (
    asynchronous,
    baseline,
    inter_block,
    isochronous,
    synchronous,
)
from ..triggers import Trigger
from ..utils import (
    generate_async_timings,
    generate_blocks_sequence,
    generate_sequence,
    search_ANT_amplifier,
    test_volume,
)
from ..utils._docs import fill_doc
from ..utils._imports import import_optional_dependency


@fill_doc
class GUI(QMainWindow):
    """Application window and layout.

    Parameters
    ----------
    ecg_ch_name : str
        Name of the ECG channel.
    %(eye_link)s
    dev : bool
        If True, a configuration with shorter sequence is loaded.
    """

    def __init__(self, ecg_ch_name: str, eye_link: EYELink, dev: bool = False):
        super().__init__()

        # define mp Queue
        self.queue = mp.Queue()

        # defaults for the peak detection
        defaults = dict(height=97.0, prominence=500.0, width=None, volume=0)

        # load configuration
        self.load_config(ecg_ch_name, defaults, eye_link, dev)

        # define window for fixation cross
        self.win = None

        # load GUI
        self.load_ui(defaults, eye_link)
        self.connect_signals_to_slots()

        # block generation
        self.all_blocks = list()
        for k in range(3):
            block = generate_blocks_sequence(self.all_blocks)
            self.all_blocks.append(block)
            self.blocks[k + 2].btype = block

        # placeholder for the last valid sequence for async blocks
        self.last_valid_timings = None

        # define Qt Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def load_config(
        self,
        ecg_ch_name: str,
        defaults: dict,
        eye_link: EYELink,
        dev: bool,
    ):
        """Set the variables and tasks arguments."""
        self.config, trigger_type = load_config(dev)
        self.tdef = load_triggers()

        # combine trigger with eye-link
        if trigger_type == "lpt":
            trigger = ParallelPortTrigger("/dev/parport0")
        elif trigger_type == "mock":
            trigger = MockTrigger()
        self.eye_link = eye_link
        self.trigger = Trigger(trigger, self.eye_link)

        # search for LSL stream
        stream_name = search_ANT_amplifier()

        # Create task mapping
        self.task_mapping = {
            "baseline": baseline,
            "synchronous": synchronous,
            "isochronous": isochronous,
            "asynchronous": asynchronous,
        }

        # Create args
        self.args_mapping = {
            "baseline": [
                self.trigger,
                self.tdef,
                self.config["baseline"]["duration"],
            ],
            "synchronous": [
                self.trigger,
                self.tdef,
                None,  # sequence
                stream_name,
                ecg_ch_name,
                defaults["height"],
                defaults["prominence"],
                defaults["width"],
                defaults["volume"],
                self.queue,
            ],
            "isochronous": [
                self.trigger,
                self.tdef,
                None,
                None,
                defaults["volume"],
            ],
            "asynchronous": [
                self.trigger,
                self.tdef,
                None,
                None,
                defaults["volume"],
            ],
        }

    # -------------------------------------------------------------------------
    def load_ui(self, defaults: dict, eye_link: EYELink):
        """Load the graphical user interface."""
        # main window
        self.setWindowTitle("Cardio-Audio-Sleep experiment")
        self.setFixedSize(QSize(800, 300))
        self.setSizePolicy(GUI._sizePolicy(self))
        self.setContextMenuPolicy(Qt.NoContextMenu)

        # main widget
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("central_widget")

        # add blocks
        self.blocks = list()
        for k in range(5):
            block = Block(self.central_widget, "")
            block.setGeometry(QRect(50 + 145 * k, 20, 120, 80))
            block.setAlignment(Qt.AlignCenter)
            block.setObjectName(f"block{k}")
            if k in (0, 1):  # disable block 0 and 1 (past)
                block.setEnabled(False)
            self.blocks.append(block)

        # add labels
        GUI._add_label(self, 50, 115, 265, 20, "past", "Previous blocks")
        GUI._add_label(self, 340, 115, 120, 20, "current", "Current")
        GUI._add_label(self, 485, 115, 265, 20, "future", "Next blocks")

        # add start / pause / stop push buttons
        self.pushButton_start = GUI._add_pushButton(
            self, 25, 150, 240, 32, "pushButton_start", "Start"
        )
        self.pushButton_pause = GUI._add_pushButton(
            self, 280, 150, 240, 32, "pushButton_pause", "Pause"
        )
        self.pushButton_stop = GUI._add_pushButton(
            self, 535, 150, 240, 32, "pushButton_stop", "Stop"
        )

        self.pushButton_pause.setEnabled(False)
        self.pushButton_pause.setCheckable(True)
        self.pushButton_stop.setEnabled(False)

        # add peak detection settings
        self.doubleSpinBox_height = GUI._add_doubleSpinBox(
            self,
            350,
            194,
            100,
            28,
            "doubleSpinBox_height",
            min_=1.0,
            max_=100.0,
            step=1.0,
            value=defaults["height"],
        )
        self.doubleSpinBox_prominence = GUI._add_doubleSpinBox(
            self,
            350,
            228,
            100,
            28,
            "doubleSpinBox_prominence",
            min_=400.0,
            max_=3000.0,
            step=25.0,
            value=defaults["prominence"],
        )
        self.doubleSpinBox_width = GUI._add_doubleSpinBox(
            self,
            350,
            262,
            100,
            28,
            "doubleSpinBox_width",
            min_=1.0,
            max_=50.0,
            step=1.0,
            value=defaults["width"],
        )
        self.pushButton_prominence = GUI._add_pushButton(
            self, 470, 228, 113, 28, "pushButton_prominence", "Disable"
        )
        self.pushButton_prominence.setCheckable(True)
        self.pushButton_prominence.setChecked(False)
        self.pushButton_width = GUI._add_pushButton(
            self, 470, 262, 113, 28, "pushButton_width", "Disable"
        )
        self.pushButton_width.setCheckable(True)
        self.pushButton_width.setChecked(False)
        GUI._add_label(self, 230, 194, 120, 28, "height", "Height")
        GUI._add_label(self, 230, 228, 120, 28, "prominence", "Prominence")
        GUI._add_label(self, 230, 262, 120, 28, "width", "Width")

        # add volume controls
        self.dial_volume = QDial(self.central_widget)
        self.dial_volume.setGeometry(QRect(25, 230, 61, 61))
        self.dial_volume.setSizePolicy(GUI._sizePolicy(self.dial_volume))
        self.dial_volume.setMinimum(0)
        self.dial_volume.setMaximum(100)
        self.dial_volume.setProperty("value", defaults["volume"])
        self.dial_volume.setObjectName("dial_volume")
        self.doubleSpinBox_volume = GUI._add_doubleSpinBox(
            self,
            100,
            247,
            80,
            24,
            "doubleSpinBox_volume",
            min_=0.0,
            max_=100.0,
            step=1.0,
            value=defaults["volume"],
        )
        self.pushButton_volume = GUI._add_pushButton(
            self, 95, 200, 80, 32, "pushButton_volume", "Test"
        )
        if sys.platform.startswith("win"):
            self.pushButton_volume.setEnabled(False)
        GUI._add_label(self, 25, 200, 60, 32, "volume", "Volume")

        # add Eye-tracker controls
        self.pushButton_calibrate = GUI._add_pushButton(
            self, 660, 228, 100, 28, "pushButton_calibrate", "Calibrate"
        )
        if isinstance(eye_link, EyelinkMock):
            self.pushButton_calibrate.setEnabled(False)
        self.pushButton_cross = GUI._add_pushButton(
            self, 660, 262, 100, 28, "pushButton_cross", "Fixation Cross"
        )
        self.pushButton_cross.setCheckable(True)
        self.pushButton_cross.setChecked(False)
        if sys.platform == "linux":
            wx = import_optional_dependency("wx", raise_error=False)
            if wx is None:
                self.pushButton_cross.setEnabled(False)
        GUI._add_label(self, 660, 190, 100, 32, "eye_tracker", "Eye Tracker")

        # add separation lines
        GUI._add_line(self, 0, 178, 800, 20, "line1", "h")
        GUI._add_line(self, 190, 188, 20, 112, "line2", "v")
        GUI._add_line(self, 600, 188, 20, 112, "line2", "v")

        # set central widget
        self.setCentralWidget(self.central_widget)

        logger.debug("UI loaded.")

    @staticmethod
    def _add_label(
        window: QMainWindow,
        x: float,
        y: float,
        w: float,
        h: float,
        name: str,
        text: str,
    ) -> QLabel:
        """Add a fix label."""
        label = QLabel(window.central_widget)
        label.setGeometry(QRect(x, y, w, h))
        label.setSizePolicy(GUI._sizePolicy(label))
        label.setAutoFillBackground(True)
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName(name)
        label.setText(text)
        return label

    @staticmethod
    def _add_line(
        window: QMainWindow,
        x: float,
        y: float,
        w: float,
        h: float,
        name: str,
        orientation: str,
    ) -> QFrame:
        """Add a line."""
        line = QFrame(window.central_widget)
        line.setGeometry(QRect(x, y, w, h))
        line.setSizePolicy(GUI._sizePolicy(line))
        if orientation == "h":
            line.setFrameShape(QFrame.HLine)
        elif orientation == "v":
            line.setFrameShape(QFrame.VLine)
        else:
            raise ValueError(
                "A line orientation should be 'h' or 'v'. "
                f"Provided: '{orientation}'."
            )
        line.setFrameShadow(QFrame.Sunken)
        line.setObjectName(name)
        return line

    @staticmethod
    def _add_pushButton(
        window: QMainWindow,
        x: float,
        y: float,
        w: float,
        h: float,
        name: str,
        text: str,
    ) -> QPushButton:
        """Add a push-button."""
        pushButton = QPushButton(window.central_widget)
        pushButton.setGeometry(QRect(x, y, w, h))
        pushButton.setSizePolicy(GUI._sizePolicy(pushButton))
        pushButton.setObjectName(name)
        pushButton.setText(text)
        return pushButton

    @staticmethod
    def _add_doubleSpinBox(
        window: QMainWindow,
        x: float,
        y: float,
        w: float,
        h: float,
        name: str,
        min_: Optional[float] = None,
        max_: Optional[float] = None,
        step: Optional[float] = None,
        value: Optional[float] = None,
    ) -> QDoubleSpinBox:
        """Add a double SpinBox."""
        doubleSpinBox = QDoubleSpinBox(window.central_widget)
        doubleSpinBox.setGeometry(QRect(x, y, w, h))
        doubleSpinBox.setSizePolicy(GUI._sizePolicy(doubleSpinBox))
        doubleSpinBox.setObjectName(name)
        if min_ is not None:
            doubleSpinBox.setMinimum(min_)
        if max_ is not None:
            doubleSpinBox.setMaximum(max_)
        if step is not None:
            doubleSpinBox.setSingleStep(step)
        if value is not None:
            doubleSpinBox.setProperty("value", value)
        return doubleSpinBox

    @staticmethod
    def _sizePolicy(widget: QWidget):
        """Set a fixed size policy."""
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(widget.sizePolicy().hasHeightForWidth())
        return sizePolicy

    # -------------------------------------------------------------------------
    def update(self):
        """Update loop.

        The update loop is called every timer tick checking if the task is
        still on going or if we can schedule the next block.
        """
        self.process.join(timeout=0.2)  # blocks 0.2 second
        if not self.process.is_alive():
            if self.process_block_name == "synchronous":
                self.sequence_timings = self.queue.get()
            if self.process_block_name == "inter-block":
                self.start_new_block()
            else:
                self.start_inter_block()

    def start_new_block(self, first: bool = False):
        """Start a new block.

        If this is the first block run, determines the 3 initial blocks.
        Else, start by rolling the blocks.
        """
        if not first:  # roll blocks
            for k, block in enumerate(self.blocks):
                if k == len(self.blocks) - 1:
                    block.btype = generate_blocks_sequence(self.all_blocks)
                    self.all_blocks.append(block.btype)
                else:
                    block.btype = self.blocks[k + 1].btype

        # determine arguments
        btype = self.blocks[2].btype
        if btype == "baseline":
            args = self.args_mapping[btype]
        else:
            args = self.args_mapping[btype]
            args[2] = generate_sequence(
                self.config[btype]["n_stimuli"],
                self.config[btype]["n_omissions"],
                self.config[btype]["edge_perc"],
                self.tdef,
            )

            if btype == "isochronous":
                args[3] = np.median(np.diff(self.sequence_timings))
                logger.info("Delay for isochronous: %.2f (s).", args[3])
            if btype == "asynchronous":
                timings, valid = generate_async_timings(self.sequence_timings)
                if valid:
                    self.last_valid_timings = timings
                    args[3] = timings
                elif not valid and self.last_valid_timings is None:
                    if timings is not None:
                        args[3] = timings
                    else:
                        logger.error(
                            "The asynchronous timings could not be generated! "
                            "Using the synchronous timing sequence instead."
                        )
                        args[3] = self.sequence_timings
                else:
                    delays = np.diff(self.last_valid_timings)
                    np.random.shuffle(delays)
                    timings = np.zeros((delays.size + 1,))
                    for k, delay in enumerate(delays):
                        timings[k + 1] = timings[k] + delay
                    args[3] = timings
                logger.info(
                    "Average delay for asynchronous: %.2f (s).",
                    np.median(np.diff(args[3])),
                )

        # start new process
        self.process = mp.Process(
            target=self.task_mapping[self.blocks[2].btype], args=tuple(args)
        )
        self.process.start()
        self.psutil_process = psutil.Process(self.process.pid)
        self.process_block_name = btype

    def start_inter_block(self):
        """Start an inter-block process that waits for a fix duration."""
        self.process = mp.Process(
            target=inter_block,
            args=(self.config["block"]["inter_block"], True),
        )
        self.process.start()
        self.psutil_process = psutil.Process(self.process.pid)
        self.process_block_name = "inter-block"

    def _update_volume(self, volume):
        """Update the volume setting."""
        self.args_mapping["synchronous"][8] = volume
        self.args_mapping["isochronous"][4] = volume
        self.args_mapping["asynchronous"][4] = volume

        logger.debug(
            "Setting the volume to %.2f -> "
            "(sync: %.1f, iso: %.1f, async: %.1f)",
            volume,
            self.args_mapping["synchronous"][8],
            self.args_mapping["isochronous"][4],
            self.args_mapping["asynchronous"][4],
        )

    def closeEvent(self, event):
        """Event called when closing the GUI."""
        if self.win is not None:
            self.win.close()
        event.accept()

    # -------------------------------------------------------------------------
    def connect_signals_to_slots(self):  # noqa: D102
        self.pushButton_start.clicked.connect(self.pushButton_start_clicked)
        self.pushButton_pause.clicked.connect(self.pushButton_pause_clicked)
        self.pushButton_stop.clicked.connect(self.pushButton_stop_clicked)

        # detection settings
        self.doubleSpinBox_height.valueChanged.connect(
            self.doubleSpinBox_valueChanged
        )
        self.doubleSpinBox_prominence.valueChanged.connect(
            self.doubleSpinBox_valueChanged
        )
        self.doubleSpinBox_width.valueChanged.connect(
            self.doubleSpinBox_valueChanged
        )
        self.pushButton_prominence.clicked.connect(
            self.pushButton_prominence_clicked
        )
        self.pushButton_width.clicked.connect(self.pushButton_width_clicked)

        # volume
        self.doubleSpinBox_volume.valueChanged.connect(
            self.doubleSpinBox_volume_valueChanged
        )
        self.dial_volume.valueChanged.connect(self.dial_volume_valueChanged)
        self.pushButton_volume.clicked.connect(self.pushButton_volume_clicked)

        # eye-tracking
        self.pushButton_calibrate.clicked.connect(
            self.pushButton_calibrate_clicked
        )
        self.pushButton_cross.clicked.connect(self.pushButton_cross_clicked)

    @pyqtSlot()
    def pushButton_start_clicked(self):
        logger.debug("Start requested.")
        self.pushButton_start.setEnabled(False)
        self.pushButton_pause.setEnabled(True)
        self.pushButton_stop.setEnabled(True)

        # start eye-tracking
        self.eye_link.start()

        # disable test sound and eye-link calibration buttons
        self.pushButton_volume.setEnabled(False)
        self.pushButton_calibrate.setEnabled(False)

        # disable cross button
        self.pushButton_cross.setEnabled(False)

        # launch first block
        self.start_new_block(first=True)

        # start timer
        self.timer.start(2000)

    @pyqtSlot()
    def pushButton_pause_clicked(self):
        self.pushButton_start.setEnabled(False)
        self.pushButton_pause.setEnabled(True)
        self.pushButton_stop.setEnabled(True)

        # change text on button
        if self.pushButton_pause.isChecked():
            logger.debug("Pause requested.")
            self.pushButton_pause.setText("Resume")
            self.timer.stop()
            try:
                self.psutil_process.suspend()
            except psutil.NoSuchProcess:
                logger.warning("No process found to suspend.")
            self.trigger.signal(self.tdef.pause)

            # enable test sound and eye-link calibration buttons
            if not sys.platform.startswith("win"):
                self.pushButton_volume.setEnabled(True)
            if not isinstance(self.eye_link, EyelinkMock):
                self.pushButton_calibrate.setEnabled(True)
        else:
            logger.debug("Resume requested.")
            self.pushButton_pause.setText("Pause")
            self.timer.start(2000)
            try:
                self.psutil_process.resume()
            except psutil.NoSuchProcess:
                logger.warning("No process found to resume.")
            self.trigger.signal(self.tdef.resume)

            # disable test sound and eye-link calibration buttons
            self.pushButton_volume.setEnabled(False)
            self.pushButton_calibrate.setEnabled(False)

    @pyqtSlot()
    def pushButton_stop_clicked(self):
        logger.debug("Stop requested.")
        # disable all interactive features
        self.pushButton_start.setEnabled(False)
        self.pushButton_pause.setEnabled(False)
        self.pushButton_stop.setEnabled(False)
        self.pushButton_volume.setEnabled(False)
        self.pushButton_calibrate.setEnabled(False)
        self.pushButton_prominence.setEnabled(False)
        self.pushButton_width.setEnabled(False)
        self.doubleSpinBox_height.setEnabled(False)
        self.doubleSpinBox_prominence.setEnabled(False)
        self.doubleSpinBox_width.setEnabled(False)
        self.dial_volume.setEnabled(False)
        self.doubleSpinBox_volume.setEnabled(False)
        self.pushButton_calibrate.setEnabled(False)
        self.pushButton_cross.setEnabled(False)

        # stop task process
        self.timer.stop()
        self.process.join(1)
        if self.process.is_alive():
            self.process.kill()

        # stop eye-tracking
        self.eye_link.stop()

    @pyqtSlot()
    def pushButton_prominence_clicked(self):
        state = self.doubleSpinBox_prominence.isEnabled()
        self.doubleSpinBox_prominence.setEnabled(not state)
        self.pushButton_prominence.setChecked(state)
        if state:  # previously enabled, now disabled
            self.args_mapping["synchronous"][6] = None
            logger.debug(
                "Disabling prominence -> %s",
                self.args_mapping["synchronous"][6],
            )
        else:  # previously disabled, now enabled
            value = self.doubleSpinBox_prominence.value()
            self.args_mapping["synchronous"][6] = value
            logger.debug(
                "Setting prominence to %.2f -> %.2f",
                value,
                self.args_mapping["synchronous"][6],
            )

    @pyqtSlot()
    def pushButton_width_clicked(self):
        state = self.doubleSpinBox_width.isEnabled()
        self.doubleSpinBox_width.setEnabled(not state)
        self.pushButton_width.setChecked(state)
        if state:  # previously enabled, now disabled
            self.args_mapping["synchronous"][7] = None
            logger.debug(
                "Disabling width -> %s", self.args_mapping["synchronous"][7]
            )
        else:  # previously disabled, now enabled
            value = self.doubleSpinBox_width.value()
            self.args_mapping["synchronous"][
                7
            ] = self.doubleSpinBox_width.value()
            logger.debug(
                "Setting width to %.2f -> %.2f",
                value,
                self.args_mapping["synchronous"][7],
            )

    @pyqtSlot()
    def doubleSpinBox_valueChanged(self):
        height = self.doubleSpinBox_height.value()
        prominence = self.doubleSpinBox_prominence.value()
        width = self.doubleSpinBox_width.value()
        prominence = (
            prominence if self.doubleSpinBox_prominence.isEnabled() else None
        )
        width = width if self.doubleSpinBox_width.isEnabled() else None

        self.args_mapping["synchronous"][5] = height
        self.args_mapping["synchronous"][6] = prominence
        self.args_mapping["synchronous"][7] = width

        logger.debug(
            "(Height, Prominence, Width) set to (%s, %s, %s) -> (%s, %s, %s)",
            height,
            None if prominence is None else round(prominence, 2),
            None if width is None else round(width, 2),
            self.args_mapping["synchronous"][5],
            self.args_mapping["synchronous"][6],
            self.args_mapping["synchronous"][7],
        )

    @pyqtSlot()
    def doubleSpinBox_volume_valueChanged(self):
        volume = self.doubleSpinBox_volume.value()
        self.dial_volume.setProperty("value", volume)
        self._update_volume(volume)

    @pyqtSlot()
    def dial_volume_valueChanged(self):
        volume = self.dial_volume.value()
        self.doubleSpinBox_volume.setProperty("value", volume)
        self._update_volume(volume)

    @pyqtSlot()
    def pushButton_volume_clicked(self):
        # sanity-check
        assert self.dial_volume.value() == self.doubleSpinBox_volume.value()
        logger.debug("Playing sound at volume %.2f.", self.dial_volume.value())
        process = mp.Process(
            target=test_volume, args=(self.dial_volume.value(),)
        )
        process.start()
        process.join()

    @pyqtSlot()
    def pushButton_calibrate_clicked(self):
        self.eye_link.calibrate()

    @pyqtSlot()
    def pushButton_cross_clicked(self):
        state = False if self.win is None else True
        self.pushButton_cross.setChecked(not state)

        if state:
            logger.debug("Removing fixation cross window.")
            self.win.close()
            self.win = None
        else:
            logger.debug("Displaying fixation cross window.")
            if not isinstance(self.eye_link, EyelinkMock):
                self.win = self.eye_link.win
            else:
                self.win = Window(
                    fullscr=True,
                    monitor=Monitor("myMonitor", width=53.0, distance=70.0),
                    winType="pyglet",
                    units="pix",
                    screen=1,
                )
            TextStim(self.win, text="+", height=100).draw()
            self.win.flip()


class Block(QLabel):
    """Widget to represent a task block.

    Parameters
    ----------
    parent : QWidget
        Parent widget.
    btype : str
        Type: 'baseline', 'synchronous', 'isochronous' or 'asynchronous'.
    """

    colors = {
        "baseline": "green",
        "synchronous": "blue",
        "isochronous": "red",
        "asynchronous": "grey",
        "": None,
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

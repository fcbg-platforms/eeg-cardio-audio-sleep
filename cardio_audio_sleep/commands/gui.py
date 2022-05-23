import multiprocessing as mp

import numpy as np
import psutil
from bsl.triggers import MockTrigger, ParallelPortTrigger
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
from ..config import load_config, load_triggers
from ..tasks import (
    asynchronous,
    baseline,
    inter_block,
    isochronous,
    synchronous,
)
from ..utils import (
    generate_async_timings,
    generate_blocks_sequence,
    generate_sequence,
    search_ANT_amplifier,
)


class GUI(QMainWindow):
    """Application window and layout.

    Parameters
    ----------
    ecg_ch_name : str
        Name of the ECG channel.
    """

    def __init__(self, ecg_ch_name: str):
        super().__init__()

        # define mp Queue
        self.queue = mp.Queue()

        # defaults for the peak detection
        defaults = dict(height=97.0, prominence=500.0, width=None, volume=0)

        # load configuration
        self.load_config(ecg_ch_name, defaults)

        # load GUI
        self.load_ui(defaults)
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
    ):
        self.config, trigger_type = load_config()
        self.tdef = load_triggers()
        if trigger_type == "lpt":
            self.trigger = ParallelPortTrigger("/dev/parport0")
        elif trigger_type == "mock":
            self.trigger = MockTrigger()
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
    def load_ui(self, defaults: dict):
        # Main window
        self.setWindowTitle("Cardio-Audio-Sleep experiment")
        self.setFixedSize(QSize(800, 300))
        self.setSizePolicy(GUI._sizePolicy(self))
        self.setContextMenuPolicy(Qt.NoContextMenu)

        # Main widget
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("central_widget")

        # Add blocks
        self.blocks = list()
        for k in range(5):
            block = Block(self.central_widget, "")
            block.setGeometry(QRect(50 + 145 * k, 20, 120, 80))
            block.setSizePolicy(GUI._sizePolicy(block))
            block.setAlignment(Qt.AlignCenter)
            block.setObjectName(f"block{k}")
            if k in (0, 1):  # disable block 0 and 1 (past)
                block.setEnabled(False)
            self.blocks.append(block)

        # Add block labels
        GUI._add_label(self, 50, 115, 265, 20, "past", "Previous blocks")
        GUI._add_label(self, 340, 115, 120, 20, "current", "Current")
        GUI._add_label(self, 485, 115, 265, 20, "future", "Next blocks")

        # Add start/pause/stop push buttons
        self.pushButton_start = QPushButton(self.central_widget)
        self.pushButton_start.setEnabled(True)
        self.pushButton_start.setGeometry(QRect(25, 150, 240, 32))
        self.pushButton_start.setSizePolicy(
            GUI._sizePolicy(self.pushButton_start)
        )
        self.pushButton_start.setObjectName("pushButton_start")
        self.pushButton_start.setText("Start")

        self.pushButton_pause = QPushButton(self.central_widget)
        self.pushButton_pause.setEnabled(False)
        self.pushButton_pause.setGeometry(QRect(280, 150, 240, 32))
        self.pushButton_pause.setSizePolicy(
            GUI._sizePolicy(self.pushButton_pause)
        )
        self.pushButton_pause.setObjectName("pushButton_pause")
        self.pushButton_pause.setText("Pause")
        self.pushButton_pause.setCheckable(True)

        self.pushButton_stop = QPushButton(self.central_widget)
        self.pushButton_stop.setEnabled(False)
        self.pushButton_stop.setGeometry(QRect(535, 150, 240, 32))
        self.pushButton_stop.setSizePolicy(
            GUI._sizePolicy(self.pushButton_stop)
        )
        self.pushButton_stop.setObjectName("pushButton_stop")
        self.pushButton_stop.setText("Stop")

        # Add peak detection settings
        self.doubleSpinBox_height = QDoubleSpinBox(self.central_widget)
        self.doubleSpinBox_height.setGeometry(QRect(540, 194, 100, 28))
        self.doubleSpinBox_height.setSizePolicy(
            GUI._sizePolicy(self.doubleSpinBox_height)
        )
        self.doubleSpinBox_height.setMinimum(0.0)
        self.doubleSpinBox_height.setMaximum(100.0)
        self.doubleSpinBox_height.setProperty("value", defaults["height"])
        self.doubleSpinBox_height.setObjectName("doubleSpinBox_height")

        self.doubleSpinBox_prominence = QDoubleSpinBox(self.central_widget)
        self.doubleSpinBox_prominence.setGeometry(QRect(540, 228, 100, 28))
        self.doubleSpinBox_prominence.setSizePolicy(
            GUI._sizePolicy(self.doubleSpinBox_prominence)
        )
        self.doubleSpinBox_prominence.setMinimum(400.0)
        self.doubleSpinBox_prominence.setMaximum(3000.0)
        self.doubleSpinBox_prominence.setSingleStep(25.0)
        self.doubleSpinBox_prominence.setProperty(
            "value", defaults["prominence"]
        )
        self.doubleSpinBox_prominence.setObjectName("doubleSpinBox_prominence")

        self.doubleSpinBox_width = QDoubleSpinBox(self.central_widget)
        self.doubleSpinBox_width.setGeometry(QRect(540, 262, 100, 28))
        self.doubleSpinBox_width.setSizePolicy(
            GUI._sizePolicy(self.doubleSpinBox_width)
        )
        self.doubleSpinBox_width.setMinimum(0.0)
        self.doubleSpinBox_width.setMaximum(50.0)
        self.doubleSpinBox_width.setProperty("value", defaults["width"])
        self.doubleSpinBox_width.setObjectName("doubleSpinBox_width")

        self.pushButton_prominence = QPushButton(self.central_widget)
        self.pushButton_prominence.setGeometry(QRect(660, 228, 113, 28))
        self.pushButton_prominence.setSizePolicy(
            GUI._sizePolicy(self.pushButton_prominence)
        )
        self.pushButton_prominence.setObjectName("pushButton_prominence")
        self.pushButton_prominence.setText("Disable")
        self.pushButton_prominence.setCheckable(True)
        self.pushButton_prominence.setChecked(False)

        self.pushButton_width = QPushButton(self.central_widget)
        self.pushButton_width.setGeometry(QRect(660, 262, 113, 28))
        self.pushButton_width.setSizePolicy(
            GUI._sizePolicy(self.pushButton_width)
        )
        self.pushButton_width.setObjectName("pushButton_width")
        self.pushButton_width.setText("Disable")
        self.pushButton_width.setCheckable(True)
        self.pushButton_width.setChecked(False)

        # Add peak detection settings labels
        GUI._add_label(self, 420, 194, 120, 28, "height", "Height")
        GUI._add_label(self, 420, 228, 120, 28, "prominence", "Prominence")
        GUI._add_label(self, 420, 262, 120, 28, "width", "Width")

        # Add peak detection GUI button
        self.pushButton_detection_gui = QPushButton(self.central_widget)
        self.pushButton_detection_gui.setGeometry(QRect(230, 208, 151, 68))
        self.pushButton_detection_gui.setSizePolicy(
            GUI._sizePolicy(self.pushButton_detection_gui)
        )
        self.pushButton_detection_gui.setObjectName("pushButton_detection_gui")
        self.pushButton_detection_gui.setText("Detection GUI")

        # Add volume controls
        self.dial_volume = QDial(self.central_widget)
        self.dial_volume.setGeometry(QRect(25, 210, 70, 68))
        self.dial_volume.setSizePolicy(GUI._sizePolicy(self.dial_volume))
        self.dial_volume.setMinimum(0)
        self.dial_volume.setMaximum(100)
        self.dial_volume.setProperty("value", defaults["volume"])
        self.dial_volume.setObjectName("dial_volume")

        self.doubleSpinBox_volume = QDoubleSpinBox(self.central_widget)
        self.doubleSpinBox_volume.setGeometry(QRect(110, 245, 80, 24))
        self.doubleSpinBox_volume.setSizePolicy(
            GUI._sizePolicy(self.doubleSpinBox_volume)
        )
        self.doubleSpinBox_volume.setMinimum(0.0)
        self.doubleSpinBox_volume.setMaximum(100.0)
        self.doubleSpinBox_volume.setProperty("value", defaults["volume"])
        self.doubleSpinBox_volume.setObjectName("doubleSpinBox_volume")

        GUI._add_label(self, 110, 215, 60, 30, "volume", "Volume")

        # Add separation lines
        GUI._add_line(self, 0, 178, 800, 20, "line1", "h")
        GUI._add_line(self, 200, 188, 20, 112, "line2", "v")

        # Set central widget
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
        """Add a fix label to the window."""
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
    def _sizePolicy(widget: QWidget):
        """A fixed size policy."""
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(widget.sizePolicy().hasHeightForWidth())
        return sizePolicy

    # -------------------------------------------------------------------------
    def update(self):
        """Update loop called every timer tick checking if the task is still
        on going or if we can schedule the next block."""
        self.process.join(timeout=0.2)  # blocks 0.2 second
        if not self.process.is_alive():
            if self.process_block_name == "synchronous":
                self.sequence_timings = self.queue.get()
            if self.process_block_name == "inter-block":
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

    # -------------------------------------------------------------------------
    def connect_signals_to_slots(self):
        self.pushButton_start.clicked.connect(self.pushButton_start_clicked)
        self.pushButton_pause.clicked.connect(self.pushButton_pause_clicked)
        self.pushButton_stop.clicked.connect(self.pushButton_stop_clicked)

        # detection settings
        self.pushButton_prominence.clicked.connect(
            self.pushButton_prominence_clicked
        )
        self.pushButton_width.clicked.connect(self.pushButton_width_clicked)
        self.pushButton_detection_gui.clicked.connect(
            self.pushButton_detection_gui_clicked
        )

        self.doubleSpinBox_height.valueChanged.connect(
            self.doubleSpinBox_valueChanged
        )
        self.doubleSpinBox_prominence.valueChanged.connect(
            self.doubleSpinBox_valueChanged
        )
        self.doubleSpinBox_width.valueChanged.connect(
            self.doubleSpinBox_valueChanged
        )

        # volume
        self.doubleSpinBox_volume.valueChanged.connect(
            self.doubleSpinBox_volume_valueChanged
        )
        self.dial_volume.valueChanged.connect(self.dial_volume_valueChanged)

    @pyqtSlot()
    def pushButton_start_clicked(self):
        logger.debug("Start requested.")
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
            logger.debug("Pause requested.")
            self.pushButton_pause.setText("Resume")
            self.timer.stop()
            try:
                self.psutil_process.suspend()
            except psutil.NoSuchProcess:
                logger.warning("No process found to suspend.")
            self.trigger.signal(self.tdef.pause)
        else:
            logger.debug("Resume requested.")
            self.pushButton_pause.setText("Pause")
            self.timer.start(2000)
            try:
                self.psutil_process.resume()
            except psutil.NoSuchProcess:
                logger.warning("No process found to resume.")
            self.trigger.signal(self.tdef.resume)

    @pyqtSlot()
    def pushButton_stop_clicked(self):
        logger.debug("Stop requested.")
        self.pushButton_start.setEnabled(False)
        self.pushButton_pause.setEnabled(False)
        self.pushButton_stop.setEnabled(False)
        self.timer.stop()
        self.process.join(1)
        if self.process.is_alive():
            self.process.kill()

    @pyqtSlot()
    def pushButton_prominence_clicked(self):
        state = self.doubleSpinBox_prominence.isEnabled()
        self.doubleSpinBox_prominence.setEnabled(not state)
        self.pushButton_prominence.setChecked(state)
        if state:
            self.args_mapping["synchronous"][6] = None
            logger.debug("Disabling prominence.")
        else:
            value = self.doubleSpinBox_prominence.value()
            self.args_mapping["synchronous"][6] = value
            logger.debug("Setting prominence to %.2f", value)

    @pyqtSlot()
    def pushButton_width_clicked(self):
        state = self.doubleSpinBox_width.isEnabled()
        self.doubleSpinBox_width.setEnabled(not state)
        self.pushButton_width.setChecked(state)
        if state:
            self.args_mapping["synchronous"][7] = None
            logger.debug("Disabling width.")
        else:
            value = self.doubleSpinBox_width.value()
            self.args_mapping["synchronous"][
                7
            ] = self.doubleSpinBox_width.value()
            logger.debug("Setting width to %.2f", value)

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
            "(Height, Prominence, Width) set to (%s, %s, %s).",
            height,
            None if prominence is None else round(prominence, 2),
            None if width is None else round(width, 2),
        )

    @pyqtSlot()
    def pushButton_detection_gui_clicked(self):
        pass

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

    def _update_volume(self, volume):
        self.args_mapping["synchronous"][8] = volume
        self.args_mapping["isochronous"][4] = volume
        self.args_mapping["asynchronous"][4] = volume

        logger.debug("Setting the volume to %.2f", volume)


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
    def btype(self) -> str:
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

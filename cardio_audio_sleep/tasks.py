from bsl.utils.lsl import list_lsl_streams
from psychopy.clock import Clock, wait
from psychopy.sound.backend_ptb import SoundPTB as Sound
import psychtoolbox as ptb

from .detector import Detector
from .triggers import ParallelPort


def synchronous():
    # Retrieve stream fron ANT amplifier
    stream_names, _ = list_lsl_streams(ignore_markers=True)
    stream_name = [stream for stream in stream_names if 'eego' in stream][0]


def isochronous():
    # Retrieve stream fron ANT amplifier
    stream_names, _ = list_lsl_streams(ignore_markers=True)
    stream_name = [stream for stream in stream_names if 'eego' in stream][0]


def asynchronous():
    # Retrieve stream fron ANT amplifier
    stream_names, _ = list_lsl_streams(ignore_markers=True)
    stream_name = [stream for stream in stream_names if 'eego' in stream][0]

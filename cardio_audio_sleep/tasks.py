from psychopy.clock import Clock, wait
from psychopy.sound.backend_ptb import SoundPTB as Sound
import psychtoolbox as ptb

from . import logger
from .detector import Detector
from .triggers import ParallelPort
from .utils.lsl import search_ANT_amplifier


def synchronous():
    stream_name = search_ANT_amplifier()


def isochronous():
    stream_name = search_ANT_amplifier()


def asynchronous():
    stream_name = search_ANT_amplifier()

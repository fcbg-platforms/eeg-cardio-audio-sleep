"""Eye-link module."""

import sys

from .. import logger
from .._typing import EYELink
from ..utils._imports import import_optional_dependency


class EyelinkMock(EYELink):
    def __init__(self, pname=None, fname=None, host_ip=None):
        logger.info("Eye-tracker: creating a MOCK eye-tracker.")
        self.el_tracker = _ElTrackerMock()

    def calibrate(self):
        logger.info("Eye-tracker: mock calibration.")

    def start(self):
        logger.info("Eye-tracker: mock start.")

    def stop(self):
        logger.info("Eye-tracker: mock stop.")

    def signal(self, value: str):
        self.el_tracker.sendMessage(value)

    def close(self):
        pass


class _ElTrackerMock:
    def __init__(self):
        pass

    def sendMessage(self, value: str):
        logger.info("Eye-tracker: mock trigger %s.", value)


pylink = import_optional_dependency("pylink", raise_error=False)
if sys.platform == "linux":
    wx = import_optional_dependency("wx", raise_error=False)
if pylink is None:
    Eyelink = EyelinkMock
elif sys.platform == "linux" and wx is None:
    Eyelink = EyelinkMock
else:
    from .EyeLink import Eyelink  # noqa: F401

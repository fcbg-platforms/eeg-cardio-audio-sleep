"""Eye-link module."""

import sys

from .._typing import EYELink
from ..utils._imports import import_optional_dependency


class EyelinkMock(EYELink):
    def __init__(self, pname=None, fname=None, host_ip=None):
        self.el_tracker = _ElTrackerMock()

    def calibrate(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def signal(self, value: str):
        pass

    def close(self):
        pass


class _ElTrackerMock:
    def __init__(self):
        pass

    def sendMessage(self, value: str):
        pass


pylink = import_optional_dependency("pylink", raise_error=False)
if sys.platform == "linux":
    wx = import_optional_dependency("wx", raise_error=False)
if pylink is None:
    Eyelink = EyelinkMock
elif sys.platform == "linux" and wx is None:
    Eyelink = EyelinkMock
else:
    from .EyeLink import Eyelink  # noqa: F401

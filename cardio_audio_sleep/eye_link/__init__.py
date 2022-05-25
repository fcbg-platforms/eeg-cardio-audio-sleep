"""Eye-link module."""

from .. import logger
from .._typing import EYELink
from ..utils._imports import import_optional_dependency


class EyelinkMock(EYELink):
    def __init__(self, pname=None, fname=None, host_ip=None):
        pass

    def calibrate(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass


pylink = import_optional_dependency("pylink", raise_error=False)
if pylink is None:
    logger.error(
        "The pylink library could not be found! Eye-tracking will " "not work."
    )
    Eyelink = EyelinkMock
else:
    from .EyeLink import Eyelink  # noqa: F401

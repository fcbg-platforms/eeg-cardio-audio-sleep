"""Eye-link module."""

import sys

from ..utils._imports import import_optional_dependency
from ._base import BaseEyelink  # noqa: F401
from .mock import EyelinkMock

pylink = import_optional_dependency("pylink", raise_error=False)
if sys.platform == "linux":
    wx = import_optional_dependency("wx", raise_error=False)
if pylink is None or (sys.platform == "linux" and wx is None):
    Eyelink = EyelinkMock
else:
    from .eye_link import Eyelink  # noqa: F401

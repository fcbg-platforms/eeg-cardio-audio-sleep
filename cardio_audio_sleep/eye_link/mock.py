from __future__ import annotations  # c.f. PEP 563, PEP 649

from typing import TYPE_CHECKING

from ._base import BaseEyelink

if TYPE_CHECKING:
    from typing import Any


class EyelinkMock(BaseEyelink):
    def __init__(self, pname: Any = None, fname: Any = None, host_ip: Any = None):
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

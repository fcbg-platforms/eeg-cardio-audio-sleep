"""Trigger using an serial port."""

from byte_triggers._base import BaseTrigger

from .utils._docs import copy_doc


class SerialTrigger(BaseTrigger):
    """Trigger using a serial port for micromed iEEG amplifiers."""

    def __init__(
        self,
    ):
        pass

    @copy_doc(BaseTrigger.signal)
    def signal(self, value: int) -> None:
        pass

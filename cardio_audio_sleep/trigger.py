from __future__ import annotations

from stimuli.trigger._base import BaseTrigger

from .utils._docs import copy_doc
from .utils._imports import import_optional_dependency


class SerialTrigger(BaseTrigger):
    """Trigger using a serial port for micromed iEEG amplifiers."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
    ) -> None:
        import_optional_dependency(
            "serial", extra="Install 'pyserial' for serial port support."
        )

        from serial import Serial, SerialException

        try:
            self._port = Serial(port, baudrate)
        except SerialException:
            raise SerialException(f"Could not open serial port at {port}.")

    @copy_doc(BaseTrigger.signal)
    def signal(self, value: int) -> None:
        value = super().signal(value)
        self._port.write(str(value).encode())

    def close(self) -> None:
        """Disconnect the serial port."""
        if hasattr(self, "_port"):
            try:
                self._port.close()
            except Exception:
                pass
            try:
                del self._port
            except Exception:
                pass

    def __del__(self):  # noqa: D105
        self.close()

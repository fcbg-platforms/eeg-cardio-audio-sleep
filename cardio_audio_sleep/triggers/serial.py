"""Trigger using an serial port."""

import threading
import time
from abc import ABC, abstractmethod
from platform import system
from typing import Union

from bsl.utils._checks import _check_type, _ensure_int
from bsl.utils._docs import copy_doc
from bsl.utils._imports import import_optional_dependency
from bsl.utils._logs import logger


class BaseTrigger(ABC):
    """Base trigger class."""

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def signal(self, value: int) -> None:
        """Send a trigger value.

        Parameters
        ----------
        value : int
            Value of the trigger, between 1 and 127.
        """
        try:
            value = int(value)
        except TypeError:
            raise TypeError(
                "The argument 'value' of a BSL trigger must be an integer "
                "between 1 and 127 included."
            )
        if not (0 < value <= 255):
            raise ValueError(
                "The argument 'value' of a BSL trigger must be an integer "
                "between 1 and 255 included."
            )


class SerialPortTrigger(BaseTrigger):
    """Trigger using a DB-9 serial port.

    Parameters
    ----------
    address : int (hex) | str
        The address of the serial port on the system.
    delay : int
        Delay in milliseconds until which a new trigger cannot be sent. During
        this time, the pins of the LPT port remain in the same state.

    Notes
    -----
    The address is specific to the system. Typical serial port address on linux
    is: /dev/ttyUSB0.
    """

    def __init__(
        self,
        address: Union[int, str],
        delay: int = 50,
    ):
        import_optional_dependency(
            "serial", extra="Install pyserial for DB-9 serial trigger support."
        )
        _check_type(address, ("int", str), "address")
        if not isinstance(address, str):
            address = _ensure_int(address)
        delay = _ensure_int(delay, "delay")
        self._delay = delay / 1000.0

        # initialize port
        self._address = address
        self._connect_serial()

        # set pins to 0 and define self._offtimer
        self._signal_off()

    def _connect_serial(self, baud_rate: int = 115200) -> None:
        """Connect to a serial port."""
        from serial import Serial, SerialException

        try:
            self._port = Serial(self._address, baud_rate)
        except SerialException:
            msg = (
                "[Trigger] Could not access serial port on "
                f"'{self._address}'."
            )
            if system() == "Linux":
                msg += (
                    " Make sure you have the permission to access this "
                    "address, e.g. by adding your user account to the "
                    "'dialout' group: 'sudo usermod -a -G dialout <username>'."
                )
            raise SerialException(msg)

        time.sleep(1)
        logger.info(
            "[Trigger] Connected to serial port on '%s'.", self._address
        )

    @copy_doc(BaseTrigger.signal)
    def signal(self, value: int) -> None:
        super().signal(value)
        if self._offtimer.is_alive():
            logger.warning(
                "[Trigger] You are sending a new signal before the end of the "
                "last signal. Signal ignored. Delay required = %.1f ms.",
                self.delay,
            )
        else:
            self._set_data(value)
            self._offtimer.start()

    def _signal_off(self) -> None:
        """Reset trigger signal to 0 and reset offtimer.

        The offtimer reset is required because threads are one-call only.
        """
        self._set_data(0)
        self._offtimer = threading.Timer(self._delay, self._signal_off)

    def _set_data(self, value: int) -> None:
        """Set data on the pin."""
        self._port.write(bytes([value]))

    def close(self) -> None:
        """Disconnects the serial port.

        This method should free the serial port and let other application or
        python process use it.
        """
        try:
            self._port.close()
        except Exception:
            pass

    def __del__(self):  # noqa: D105
        self.close()

    # --------------------------------------------------------------------
    @property
    def address(self) -> Union[int, str]:
        """The address of the serial port on the system.

        :type: int | str
        """
        return self._address

    @property
    def delay(self) -> float:
        """Delay (ms) to wait between two :meth:`~SerialPortTrigger.signal`.

        :type: float
        """
        return self._delay * 1000.0

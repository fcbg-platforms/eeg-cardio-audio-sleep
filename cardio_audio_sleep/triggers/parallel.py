import threading

from psychopy.parallel import ParallelPort as PPort

from bsl.triggers._trigger import _Trigger
from bsl.utils._docs import fill_doc, copy_doc
from bsl.utils._checks import _check_type
from bsl.utils._logs import logger


@fill_doc
class ParallelPort(_Trigger):
    """
    Trigger using a parallel port (LPT).

    Parameters
    ----------
    address : hex | `int` | `str`
        The address of the parallel port on the system.
        On Linux::

            LPT1 = /dev/parport0
            LPT2 = /dev/parport1
            LPT3 = /dev/parport2

        On Windows, commom port addresses::

            LPT1 = 0x0378 or 0x03BC
            LPT2 = 0x0278 or 0x0378
            LPT3 = 0x0278

        macOS does not have support for parallel ports.
    %(trigger_lpt_delay)s
    %(trigger_verbose)s
    """

    def __init__(self, address, delay: int = 50, *, verbose: bool = True):
        _check_type(delay, ('int', ), item_name='delay')
        super().__init__(verbose)
        self._address = address
        self._delay = delay / 1000.0

        self._pport = PPort(self._address)
        self._offtimer = threading.Timer(self._delay, self._signal_off)

    @copy_doc(_Trigger.signal)
    def signal(self, value: int) -> bool:
        _check_type(value, ('int', ), item_name='value')
        if self._offtimer.is_alive():
            logger.warning(
                'You are sending a new signal before the end of the last '
                'signal. Signal ignored. Delay required = {self.delay} ms.')
            return False
        self._set_data(value)
        super().signal(value)
        self._offtimer.start()
        return True

    def _signal_off(self):
        """
        Reset trigger signal to 0 and reset offtimer as Threads are one-call
        only.
        """
        self._set_data(0)
        self._offtimer = threading.Timer(self._delay, self._signal_off)

    @copy_doc(_Trigger._set_data)
    def _set_data(self, value: int):
        super()._set_data(value)
        self._pport.setData(value)

    def __del__(self):
        if hasattr(self, '_pport'):
            del self._pport

    # --------------------------------------------------------------------
    @property
    def address(self):
        """
        Port address.

        :type: `int`
        """
        return self._address

    @property
    def delay(self):
        """
        Delay to wait between two ``.signal()`` call in milliseconds.

        :type: `float`
        """
        return self._delay * 1000.0

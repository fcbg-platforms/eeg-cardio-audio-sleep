from bsl.triggers import LSLTrigger

from .._typing import EYELink
from ..utils._docs import fill_doc


@fill_doc
class Trigger:
    """Trigger class combining a BSL trigger (LPT) and an eye-link system.

    Parameters
    ----------
    trigger : Trigger
        A BSL trigger instance.
    %(eye_link)s
    """

    def __init__(self, trigger, eye_link: EYELink, instruments: bool = True):
        if isinstance(trigger, LSLTrigger):
            raise RuntimeError(
                "The BSL trigger can not be an LSL trigger as "
                "it is incompatible with multiprocessing."
            )
        self._trigger = trigger
        self._eye_link = eye_link

    def signal(self, value: int) -> None:
        """Send a trigger value.

        Parameters
        ----------
        value : int
            Value sent on the trigger channel.
        """
        self._trigger.signal(value)
        self._eye_link.signal(str(value))

    @property
    def trigger(self):
        """BSL Trigger instance."""
        return self._trigger

    @property
    def eye_link(self):
        return self._eye_link

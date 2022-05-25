from .._typing import EYELink
from ..utils._docs import fill_doc


@fill_doc
class Trigger:
    """
    Trigger class combining a BSL trigger (LPT) and an eye-link system.

    Parameters
    ----------
    trigger : Trigger
        A BSL trigger instance.
    %(eye_link)s
    """

    def __init__(self, trigger, eye_link: EYELink):
        self.trigger = trigger
        self.eye_link = eye_link

    def signal(self, value: int):
        """
        Send a trigger value.

        Parameters
        ----------
        value : int
            Value sent on the trigger channel.
        """
        self.trigger.signal(value)
        self.eye_link.el_tracker.sendMessage(str(value))

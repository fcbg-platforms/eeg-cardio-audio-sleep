from bsl.externals import pylsl

from .. import logger
from .._typing import EYELink
from ..utils._checks import _check_type
from ..utils._docs import fill_doc


@fill_doc
class Trigger:
    """Trigger class combining a BSL trigger (LPT) and an eye-link system.

    Parameters
    ----------
    trigger : Trigger
        A BSL trigger instance.
    %(eye_link)s
    instruments : bool
        If True, an LSL outlet is created and the method signal_instrument
        can be used to push a string on the outlet.
    """

    def __init__(self, trigger, eye_link: EYELink, instruments: bool = True):
        self._trigger = trigger
        self._eye_link = eye_link

        # stream outlet for instruments
        if instruments:
            self._sinfo = pylsl.StreamInfo(
                name="instruments",
                type="Markers",
                channel_count=1,
                nominal_srate=pylsl.IRREGULAR_RATE,
                channel_format=pylsl.cf_string,
                source_id="instruments",
            )
            self._outlet = pylsl.StreamOutlet(self._sinfo)
        else:
            self._sinfo = None
            self._outlet = None

    def signal(self, value: int) -> None:
        """Send a trigger value.

        Parameters
        ----------
        value : int
            Value sent on the trigger channel.
        """
        self._trigger.signal(value)
        self._eye_link.signal(str(value))

    def signal_instrument(self, value: str) -> None:
        """Send an instrument filename on the LSL outlet.

        Parameters
        ----------
        value : str
            Value sent on the LSL outlet.
        """
        if self._outlet is None:
            logger.error(
                "The LSL outlet to push instrument filenames was not "
                "created. Skipping."
            )
            return None
        _check_type(value, (str,), "value")
        self._oulet.push_sample([value])

    def close(self) -> None:
        """Close the LSL outlet."""
        try:
            del self._outlet
        except Exception:
            pass

    @property
    def trigger(self):
        """BSL Trigger instance."""
        return self._trigger

    @property
    def eye_link(self):
        return self._eye_link

    @property
    def sinfo(self) -> pylsl.StreamInfo:
        """LSL stream info."""
        return self._sinfo

    @property
    def _outlet(self) -> pylsl.StreamOutlet:
        """LSL stream outlet."""
        return self._outlet

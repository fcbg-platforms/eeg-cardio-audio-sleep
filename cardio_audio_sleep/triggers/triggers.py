from bsl.externals import pylsl
from bsl.triggers import LSLTrigger

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


class TriggerInstrument:
    """Trigger class for sending instrument filenames on an LSL outlet."""

    def __init__(self):
        self._sinfo = pylsl.StreamInfo(
            name="instruments",
            type="Markers",
            channel_count=1,
            nominal_srate=pylsl.IRREGULAR_RATE,
            channel_format=pylsl.cf_string,
            source_id="instruments",
        )
        self._outlet = pylsl.StreamOutlet(self._sinfo)

    def signal(self, value: str) -> None:
        """Send an instrument filename on the LSL outlet.

        Parameters
        ----------
        value : str
            Value sent on the LSL outlet.
        """
        _check_type(value, (str,), "value")
        self._outlet.push_sample([value])

    def close(self) -> None:
        """Close the LSL outlet."""
        try:
            del self._outlet
        except Exception:
            pass

    def __del__(self):  # noqa: D105
        self.close()

    @property
    def sinfo(self) -> pylsl.StreamInfo:
        """LSL stream info."""
        return self._sinfo

    @property
    def outlet(self) -> pylsl.StreamOutlet:
        """LSL stream outlet."""
        return self._outlet

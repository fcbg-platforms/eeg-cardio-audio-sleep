from pathlib import Path

from bsl.triggers import TriggerDef


def load_triggers():
    """
    Load triggers from triggers.ini into a TriggerDef instance.

    Returns
    -------
    tdef : TriggerDef
        Trigger definitiopn containing: sound, omission, sync_start, sync_stop,
        iso_start, iso_stop, async_start, async_stop, baseline_start and
        baseline_stop
    """
    directory = Path(__file__).parent
    tdef = TriggerDef(directory / 'triggers.ini')

    keys = (
        'sound',
        'omission',
        'sync_start',
        'sync_stop',
        'iso_start',
        'iso_stop',
        'async_start',
        'async_stop',
        'baseline_start',
        'baseline_stop'
        )
    for key in keys:
        if not hasattr(tdef, key):
            raise ValueError(
                f"Key '{key}' is missing from trigger definition.")

    return tdef

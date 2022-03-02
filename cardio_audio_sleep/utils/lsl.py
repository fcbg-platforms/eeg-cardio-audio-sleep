from bsl.utils.lsl import list_lsl_streams, search_lsl

from ._logs import logger


def search_ANT_amplifier():
    """Looks for ANT Neuro amplifier on the LSL network.

    Returns
    -------
    stream_name : str
        Name of the ANT Neuro LSL stream. Typically 'eego {serial number}'.
    """
    stream_names, _ = list_lsl_streams(ignore_markers=True)
    stream_name = [stream for stream in stream_names if 'eego' in stream]
    if len(stream_name) == 1:
        logger.info("Found LSL stream fron ANT Neuro amplifier.")
        stream_name = stream_name[0]
    else:
        logger.warning(
            "Multiple LSL streams found matching the ANT Neuro amplifier "
            "'eego' name. Please select a stream manually.")
        stream_name = search_lsl(ignore_markers=True, timeout=5)

    if 'eego' not in stream_name:
        raise RuntimeError("ANT Neuro amplifier could not be found.")

    return stream_name

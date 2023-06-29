from bsl.utils.lsl import list_lsl_streams, search_lsl

from ._checks import _check_type, _check_value
from ._logs import logger


def search_amplifier(amp_type: str = "ant") -> str:
    """Look for an (i)EEG amplifier on the LSL network.

    Parameters
    ----------
    amp_type : "ant" | "micromed"
        Type of amplifier to look for.

    Returns
    -------
    stream_name : str
        Name of the LSL stream.
    """
    _check_type(amp_type, (str,), "amp_type")
    _check_value(amp_type, ("ant", "micromed"), "amp_type")
    stream_names, _ = list_lsl_streams(ignore_markers=True)
    if amp_type == "ant":
        stream_names = [stream for stream in stream_names if "eego" in stream]
    elif amp_type == "micromed":
        stream_names = stream_names
    if len(stream_names) == 1:
        logger.info("Found LSL stream from EEG amplifier.")
        stream_name = stream_names[0]
    elif 1 < len(stream_names):
        logger.warning(
            "Multiple LSL streams found matching the amplifier type "
            "name. Please select a stream manually."
        )
        stream_name = search_lsl(ignore_markers=True, timeout=5)
    else:
        stream_name = ""

    if amp_type == "ant" and "eego" not in stream_name:
        raise RuntimeError("ANT Neuro amplifier could not be found.")

    return stream_name

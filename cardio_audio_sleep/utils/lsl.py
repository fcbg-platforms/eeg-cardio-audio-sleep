from warnings import warn

from mne_lsl.lsl import resolve_streams

from .logs import _use_log_level, logger


def search_amplifier() -> str:
    """Look for an (i)EEG amplifier on the LSL network.

    Returns
    -------
    stream_name : str
        Name of the LSL stream.
    """
    sinfos = [sinfo for sinfo in resolve_streams(timeout=5) if sinfo.sfreq != 0]
    if len(sinfos) == 0:
        raise RuntimeError("Could not find LSL stream from amplifier.")
    elif len(sinfos) == 1:
        logger.info("Found LSL stream from amplifier:\n\n%s\n", sinfos[0])
        stream_name = sinfos[0].name
    else:
        warn(
            "Multiple LSL stream found on the network. Please select a stream "
            "manually.",
            RuntimeWarning,
            stacklevel=2,
        )
        with _use_log_level("INFO"):
            logger.info("-- List of LSL servers --")
            for k, sinfo in enumerate(sinfos):
                logger.info("%i: %s", k, sinfo.name)
        index = input(
            "Stream index? Hit enter without index to select the first server.\n>> "
        )
        index = 0 if index.strip() == "" else int(index.strip())
        stream_name = sinfos[index].name
    return stream_name

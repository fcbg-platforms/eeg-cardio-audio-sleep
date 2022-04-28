from .. import logger

RETRIES = 3


def input_ecg_ch_name():
    """Input function for channel name (str)."""
    msg = "[IN] Input the ECG channel name:\n>>> "
    value = input(msg)
    return value


def input_peak_height_perc():
    """Input function for peak detection settings height_perc."""
    msg = "[IN] Input the peak height percentage parameter:\n>>> "
    attempt = 1
    while attempt <= RETRIES:
        try:
            value = float(input(msg).strip())
            assert 0 < value < 100
            break
        except Exception:
            logger.warning(
                'The peak height percentage parameter must be a float '
                'between 0 and 100 (%).')
            attempt += 1
    else:
        raise RuntimeError('Too many erroneous answers provided.')

    return value


def input_peak_prominence():
    """Input function for peak detection settings prominence."""
    msg = "[IN] Input the peak prominence parameter (use None to disable):" + \
        "\n>>> "
    attempt = 1
    while attempt <= RETRIES:
        try:
            value = input(msg)
            if value.lower().strip() == 'none':
                return None
            else:
                value = float(value.strip())
                assert 0 < value
                break
        except Exception:
            logger.warning(
                'The peak prominence parameter must be a strictly positive '
                'float.')
            attempt += 1
    else:
        raise RuntimeError('Too many erroneous answers provided.')

    return value


def input_peak_width():
    """Input function for peak detection settings width."""
    msg = "[IN] Input the peak width parameter (use None to disable):" + \
        "\n>>> "
    attempt = 1
    while attempt <= RETRIES:
        try:
            value = input(msg)
            if value.lower().strip() == 'none':
                return None
            else:
                value = float(value.strip())
                assert 0 < value
                break
        except Exception:
            logger.warning(
                'The peak width parameter must be a strictly positive '
                'float.')
            attempt += 1
    else:
        raise RuntimeError('Too many erroneous answers provided.')

    return value

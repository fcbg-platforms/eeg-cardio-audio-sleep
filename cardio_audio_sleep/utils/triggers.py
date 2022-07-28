def convert(k: int) -> int:
    """Convert trigger to high-pin, skipping the 4 first pins.

    Examples
    --------
    k=3 corresponds to "11"" in binary.
    If the 4 first pins are skipped, it corresponds to "110000".
    Which corresponds to 48 in decimal.
    """
    binary = bin(k)[2:] + "0000"
    return int(binary, 2)

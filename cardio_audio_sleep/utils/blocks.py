import random

_BLOCKS: set[str] = {
    "baseline",
    "isochronous",
    "asynchronous",
    "synchronous-respiration",
    "synchronous-cardiac",
}


def generate_blocks_sequence(previous_blocks: list[str]) -> str:
    """Create a semi-random block sequence.

    Parameters
    ----------
    previous_blocks : list
        List of previously generated blocks.

    Returns
    -------
    block : str
        The next block selected among the options.
    """
    if len(previous_blocks) == 0:
        return "baseline"  # Start with baseline
    elif len(previous_blocks) == 1:
        return "synchronous-respiration"  # Followed by synchronous-respiration
    # above that, look by group of 5
    idx = len(previous_blocks) % 5
    if idx == 0:
        return random.choice([val for val in _BLOCKS if val != previous_blocks[-1]])
    else:
        segment = previous_blocks[-idx:]
        return random.choice(tuple(_BLOCKS - set(segment)))

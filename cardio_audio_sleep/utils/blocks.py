import random


def generate_blocks_sequence(previous_blocks: list) -> str:
    """
    Create a valid block sequence.

    Parameters
    ----------
    previous_blocks : list
        List of previously generated blocks

    Returns
    -------
    block : str
        The next block selected among the options.
    """
    options = ("baseline", "synchronous", "isochronous", "asynchronous")

    if len(previous_blocks) == 0:
        return "baseline"  # Start with baseline
    elif len(previous_blocks) == 1:
        return "synchronous"  # Followed by synchronous

    # Above that, look by group of 4
    idx = len(previous_blocks) % 4
    if idx == 0:
        return random.choice(
            [val for val in options if val != previous_blocks[-1]]
        )
    else:
        segment = previous_blocks[-idx:]
        return random.choice(tuple(set(options) - set(segment)))

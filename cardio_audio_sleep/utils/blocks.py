import random


def generate_blocks_sequence(previous_blocks):
    """
    Creates a valid block sequence.

    Parameters
    ----------
    previous_blocks : list
        List of previously generated blocks
    """
    options = ('baseline', 'synchronous', 'isochronous', 'asynchronous')

    if len(previous_blocks) == 0:
        return 'baseline'  # Start with baseline
    elif len(previous_blocks) == 1:
        return 'synchronous'  # Followed by synchronous
    elif len(previous_blocks) == 2:
        return random.choice(('isochronous', 'asynchronous'))  # only 2 options
    elif len(previous_blocks) == 3:
        return tuple(set(options) - set(previous_blocks))[0]

    # Above that, look by group of 4
    idx = len(previous_blocks) % 4
    if idx == 0:
        return random.choice([val for val in options
                              if val != previous_blocks[-1]])
    else:
        segment = previous_blocks[-idx:]
        return random.choice(tuple(set(options) - set(segment)))

from itertools import groupby
import math
import random
from typing import Union

import numpy as np
from numpy.typing import NDArray

from ._checks import _check_type, _check_value
from ._logs import logger


def generate_sequence(
        size: int,
        omissions: int,
        edge_perc: Union[int, float],
        tdef,
        max_iter: int = 500,
        on_diverge: str = 'warn',
        ) -> NDArray[int]:
    """
    Creates a valid sequence.
    - 300 sounds / block
    - 20% (60) are omissions

    An omission should not be in the first or last 5%.
    Omissions should not be consecutive.

    Parameters
    ----------
    size : int
        Total number of elements in the sequence.
    omissions : int
        Total number of omissions in the sequence.
    edge_perc : float
        Percentage of the total number of elements that have to be sound at
        the beginning and at the end of the sequence.
    tdef : TriggerDef
        Trigger definition instance. Must contain the keys:
            - sound (aligned on sequence)
            - omission (aligned on sequence)
    max_iter : int
        Maximum numnber of iteration to randomize the sequence.
    on_diverge : str
        Either 'warn' to log an error message or 'raise' to raise a
        RuntimeError when the randomization does not converge within the
        maximum number of iteration allowed.
    """
    _check_type(size, ('int', ), 'size')
    _check_type(omissions, ('int', ), 'omissions')
    _check_type(edge_perc, ('numeric', ), 'edge_perc')
    _check_type(max_iter, ('int', ), 'max_iter')
    _check_value(on_diverge, ('warn', 'raise'), 'on_diverge')
    if size <= 0:
        raise ValueError(
            "Argument 'size' must be a strictly positive integer. "
            f"Provided: '{size}'.")
    if omissions < 0:
        raise ValueError(
            "Argument 'omissions' must be a strictly positive integer. "
            f"Provided: '{omissions}'.")
    if not (0 <= edge_perc <= 100):
        raise ValueError(
            "Argument 'edge_perc' must be a valid percentage between 0 and "
            f"100. Provided {edge_perc}%.")
    if max_iter <= 0:
        raise ValueError(
            "Argument 'max_iter' must be a strictly positive integer. "
            f"Provided: '{max_iter}'.")

    n_edge = math.ceil(edge_perc * size / 100)
    start = [tdef.sound] * n_edge

    middle = [tdef.sound] * (size - omissions - 2 * n_edge)
    middle += [tdef.omission] * omissions
    random.shuffle(middle)
    iter_ = 0
    while True:
        groups = [(n, list(group)) for n, group in groupby(middle)]

        if all(len(group[1]) == 1
               for group in groups if group[0] == tdef.omission):
            converged = True
            break

        if max_iter < iter_:
            msg = "Randomize sequence generation could not converge."
            if on_diverge == 'warn':
                logger.warning(msg)
                converged = False
            else:
                raise RuntimeError(msg)
            break

        for i, (n, group) in enumerate(groups):
            if n == tdef.sound or len(group) == 1:
                continue

            # find the longest group of TRIGGERS['sound']
            idx = np.argmax([len(g) if n == tdef.sound else 0
                             for n, g in groups])
            pos_sound = sum(len(g) for k, (_, g) in enumerate(groups)
                            if k < idx)
            pos_sound = pos_sound + len(groups[idx][1]) // 2  # center

            # find position of current group
            pos_omission = sum(len(g) for k, (_, g) in enumerate(groups)
                               if k < i)

            # swap first element from omissions with center of group of sounds
            middle[pos_sound], middle[pos_omission] = \
                middle[pos_omission], middle[pos_sound]

            break

        iter_ += 1

    # sanity-check
    if converged:
        assert all(len(group) == 1
                   for n, group in groups if n == tdef.omission)
        assert not any(middle[i-1] == middle[i] == tdef.omission
                       for i in range(1, len(middle)))

    end = [tdef.sound] * n_edge
    return np.array(start + middle + end)

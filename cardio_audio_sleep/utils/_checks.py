"""Utility functions for checking types and values. Inspired from MNE."""

import os
import logging
import operator
from pathlib import Path
from typing import Union

from bsl.triggers import TriggerDef
import numpy as np
from numpy.typing import ArrayLike

from ._logs import logger


def _ensure_int(item, item_name=None):
    """
    Ensure a variable is an integer.

    Parameters
    ----------
    item : object
        Item to check.
    item_name : str | None
        Name of the item to show inside the error message.

    Raises
    ------
    TypeError
        When the type of the item is not int.
    """
    # This is preferred over numbers.Integral, see:
    # https://github.com/scipy/scipy/pull/7351#issuecomment-299713159
    try:
        # someone passing True/False is much more likely to be an error than
        # intentional usage
        if isinstance(item, bool):
            raise TypeError
        item = int(operator.index(item))
    except TypeError:
        item_name = "Item" if item_name is None else "'%s'" % item_name
        raise TypeError("%s must be an int, got %s instead."
                        % (item_name, type(item)))

    return item


class _IntLike:
    @classmethod
    def __instancecheck__(cls, other):
        try:
            _ensure_int(other)
        except TypeError:
            return False
        else:
            return True


class _Callable:
    @classmethod
    def __instancecheck__(cls, other):
        return callable(other)


_types = {
    "numeric": (np.floating, float, _IntLike()),
    "path-like": (str, Path, os.PathLike),
    "int": (_IntLike(), ),
    "callable": (_Callable(), ),
}


def _check_type(item, types, item_name=None):
    """
    Check that item is an instance of types.

    Parameters
    ----------
    item : object
        Item to check.
    types : tuple of types | tuple of str
        Types to be checked against.
        If str, must be one of:
            ('int', 'str', 'numeric', 'path-like', 'callable')
    item_name : str | None
        Name of the item to show inside the error message.

    Raises
    ------
    TypeError
        When the type of the item is not one of the valid options.
    """
    check_types = sum(((type(None), ) if type_ is None else (type_, )
                       if not isinstance(type_, str) else _types[type_]
                       for type_ in types), ())

    if not isinstance(item, check_types):
        type_name = ["None" if cls_ is None else cls_.__name__
                     if not isinstance(cls_, str) else cls_
                     for cls_ in types]
        if len(type_name) == 1:
            type_name = type_name[0]
        elif len(type_name) == 2:
            type_name = ' or '.join(type_name)
        else:
            type_name[-1] = "or " + type_name[-1]
            type_name = ", ".join(type_name)
        item_name = "Item" if item_name is None else "'%s'" % item_name
        raise TypeError(f"{item_name} must be an instance of {type_name}, "
                        f"got {type(item)} instead.")

    return item


def _check_value(item, allowed_values, item_name=None, extra=None):
    """
    Check the value of a parameter against a list of valid options.

    Parameters
    ----------
    item : object
        Item to check.
    allowed_values : tuple of objects
        Allowed values to be checked against.
    item_name : str | None
        Name of the item to show inside the error message.
    extra : str | None
        Extra string to append to the invalid value sentence, e.g.
        "when using ico mode".

    Raises
    ------
    ValueError
        When the value of the item is not one of the valid options.
    """
    if item not in allowed_values:
        item_name = "" if item_name is None else " '%s'" % item_name
        extra = "" if extra is None else " " + extra
        msg = ("Invalid value for the{item_name} parameter{extra}. "
               '{options}, but got {item!r} instead.')
        allowed_values = tuple(allowed_values)  # e.g., if a dict was given
        if len(allowed_values) == 1:
            options = "The only allowed value is %s" % repr(allowed_values[0])
        elif len(allowed_values) == 2:
            options = "Allowed values are %s and %s" % \
                (repr(allowed_values[0]), repr(allowed_values[1]))
        else:
            options = "Allowed values are "
            options += ", ".join([f"{repr(v)}" for v in allowed_values[:-1]])
            options += f", and {repr(allowed_values[-1])}"
        raise ValueError(msg.format(item_name=item_name, extra=extra,
                                    options=options, item=item))

    return item


def _check_verbose(verbose):
    """
    Check that the value of verbose is valid.
    """
    logging_types = dict(
        DEBUG=logging.DEBUG,
        INFO=logging.INFO,
        WARNING=logging.WARNING,
        ERROR=logging.ERROR,
        CRITICAL=logging.CRITICAL)

    _check_type(verbose, (bool, str, int, None), item_name='verbose')

    if verbose is None:
        verbose = 'INFO'
    elif isinstance(verbose, str):
        verbose = verbose.upper()
        _check_value(verbose, logging_types, item_name='verbose')
        verbose = logging_types[verbose]
    elif isinstance(verbose, bool):
        if verbose:
            verbose = 'INFO'
        else:
            verbose = 'WARNING'

    return verbose


def _check_tdef(tdef):
    """
    Checks that the trigger definition contains all the required keys.
    """
    _check_type(tdef, (TriggerDef, ), 'tdef')
    keys = ('sound', 'omission',
            'sync_start', 'sync_stop',
            'iso_start', 'iso_stop',
            'async_start', 'async_stop',
            'baseline_start', 'baseline_stop')
    assert all(hasattr(tdef, attribute) for attribute in keys)


def _check_sequence(
        sequence: ArrayLike,
        tdef
        ):
    """
    Checks that the sequence is valid.
    """
    _check_type(sequence, (list, tuple, np.ndarray), 'sequence')
    if isinstance(sequence, (list, tuple)):
        sequence = np.array(sequence)
    elif len(sequence.shape) != 1:
        raise ValueError(
            "Argument 'sequence' should be a 1D iterable and not a "
            f"{len(sequence.shape)}D iterable. ")

    valids = (tdef.sound, tdef.omission)
    if any(elt not in valids for elt in sequence):
        raise ValueError(
            "Unknown value within 'sequence'. All elements should be among "
            f"'{valids}'.")

    logger.info('Provided sequence contains %s elements.', sequence.size)

    return sequence


def _check_sequence_timings(
        sequence_timings: ArrayLike,
        sequence: ArrayLike,
        min_distance: Union[int, float] = 0.1  # sound duration
        ):
    """
    Checks that the sequence timings are valid.
    """
    _check_type(sequence_timings, (list, tuple, np.ndarray),
                'sequence_timings')
    if isinstance(sequence_timings, (list, tuple)):
        sequence_timings = np.array(sequence_timings)
    elif len(sequence_timings.shape) != 1:
        raise ValueError(
            "Argument 'sequence_timings' should be a 1D iterable and not a "
            f"{len(sequence_timings.shape)}D iterable. ")

    if sequence.size != sequence_timings.size:
        raise ValueError(
            "Arguments 'sequence' and 'sequence_timings' did not have the "
            "same number of elements.")

    if any(elt < 0 for elt in sequence_timings):
        raise ValueError(
            "All sequence timings should be strictly positive integers, "
            "except the first timing equal to 0.")

    if sequence_timings[0] != 0:
        sequence_timings -= sequence_timings[0]

    if any(elt <= min_distance for elt in np.diff(sequence_timings)):
        raise ValueError(
            "All sequence timings should be separated by at least "
            f"{min_distance} seconds.")

    return sequence_timings

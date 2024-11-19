from __future__ import annotations

import time

import click
import numpy as np
from mne_lsl.lsl import local_clock

from .. import set_log_level
from ..detector import Detector
from ..tasks._config import ECG_DISTANCE, ECG_HEIGHT, ECG_PROMINENCE, TRIGGERS
from ..tasks._utils import create_trigger, generate_sequence
from ._utils import ch_name_ecg, fq_deviant, fq_target, no_viewer, stream, verbose


@click.command()
@stream
@ch_name_ecg
@click.option(
    "--n-peaks", prompt="Number of peaks", help="Number of peaks to detect.", type=int
)
@no_viewer
@verbose
def test_detector(
    stream: str,
    ch_name_ecg: str,
    n_peaks: int,
    no_viewer: bool,
    verbose: str,
) -> None:
    """Test the cardiac detector settings."""
    set_log_level(verbose)
    if n_peaks <= 0:
        raise ValueError("The number of peaks must be greater than 0.")
    detector = Detector(
        stream_name=stream,
        ecg_ch_name=ch_name_ecg,
        resp_ch_name=None,
        ecg_height=ECG_HEIGHT,
        ecg_distance=ECG_DISTANCE,
        ecg_prominence=ECG_PROMINENCE,
        resp_prominence=None,
        resp_distance=None,
        viewer=not no_viewer,
    )
    counter = 0
    while counter < n_peaks:
        peak = detector.new_peak("ecg")
        if peak is not None:
            delay = local_clock() - peak
            counter += 1
            click.echo(f"ECG peak {counter} / {n_peaks} detected after {delay:.3f}s.")


@click.command()
@fq_target
@fq_deviant
@verbose
def test_sequence(target: float, deviant: float, verbose: str) -> None:
    """Test the sequence generation settings."""
    from matplotlib import pyplot as plt

    set_log_level(verbose)
    sequence = generate_sequence(target, deviant)
    trigger_target = TRIGGERS[f"target/{target}"]
    trigger_deviant = TRIGGERS[f"deviant/{deviant}"]
    f, ax = plt.subplots(1, 1, layout="constrained")
    idx = np.where(sequence == trigger_target)[0]
    ax.scatter(idx, np.ones(idx.size) * trigger_target, color="teal", label="target")
    idx = np.where(sequence == trigger_deviant)[0]
    ax.scatter(idx, np.ones(idx.size) * trigger_deviant, color="coral", label="deviant")
    ax.set_xlabel("Stimulus number")
    ax.set_ylabel("Trigger")
    ax.set_title("Sequence of stimuli")
    ax.legend()
    plt.show(block=True)


@click.command()
@verbose
def test_triggers(verbose: str) -> None:
    """Test the trigger settings."""
    set_log_level(verbose)
    trigger = create_trigger()
    for key, value in TRIGGERS.items():
        click.echo(f"Trigger {key}: {value}")
        trigger.signal(value)
        time.sleep(0.5)

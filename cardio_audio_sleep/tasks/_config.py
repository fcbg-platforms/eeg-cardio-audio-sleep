from __future__ import annotations

from ._config_detector import ECG_DISTANCE, ECG_HEIGHT, ECG_PROMINENCE

# TRIGGERS must contain 2 keys, 'sound' and 'omission'.
# For TRIGGER_ARGS:
# - 'serial' -> COM Port, e.g. '/dev/ttyUSB0'
# - 'lpt' -> port address, e.g. '/dev/parport0'
# - 'arduino' -> None
# - 'mock' -> None
TRIGGERS: dict[str, int] = {"sound": 1, "omission": 2}
TRIGGER_TYPE: str = "arduino"  # one of 'arduino', 'serial', 'lpt', 'mock'
TRIGGER_ARGS: str | int | None = None
TRIGGER_TASKS: dict[str, tuple[int, int]] = {
    "baseline": (4, 5),
    "synchronous": (8, 9),
    "isochronous": (16, 17),
    "asynchronous": (32, 33),
}
# sound settings
SOUND_FREQUENCY: float = 1000.0  # pure tone frequency in Hz
SOUND_DURATION: float = 0.2
N_SOUND: int = 50
N_OMISSION: int = 10
BACKEND: str = "ptb"  # "ptb" or "stimuli" to select the audio playback backend
DEVICE: str | int | None = None  # None to use the default device
BLOCKSIZE: int = 4  # default 128, controls part of the latency <-> stability trade-off
# sequence and task settings
BASELINE_DURATION: float = 60  # default setting when nothing is available
EDGE_PERC: float = 10  # percentage between 0 and 100 in which deviant are absent
OUTLIER_PERC: float = 10  # percentage between 0 and 100 to remove outliers PTP delays
# target timing
TARGET_DELAY: float = 0.25
# other
INTER_BLOCK_DELAY: float = 5  # delay in seconds between blocks


# TODO: Define a configuration class to handle all configuration elements.
class ConfigRepr:  # noqa: D101
    def __repr__(self) -> str:
        """String representation of the configuration."""  # noqa: D401
        repr_str = "Configuration of the system:\n"
        repr_str += len(repr_str.strip()) * "-" + "\n"
        # triggers
        repr_str += f"Triggers:\n  type: {TRIGGER_TYPE}\n"
        if TRIGGER_ARGS is not None:
            repr_str += f"  args: {TRIGGER_ARGS}\n"
        repr_str += "  codes:\n"
        for key, value in TRIGGERS.items():
            repr_str += f"    {key}: {value}\n"
        # sounds
        repr_str += "Sounds:\n"
        repr_str += f"  frequency: {SOUND_FREQUENCY} Hz\n"
        repr_str += f"  duration: {SOUND_DURATION} s\n"
        repr_str += f"  number of sound: {N_SOUND}\n"
        repr_str += f"  number of omission: {N_OMISSION}\n"
        repr_str += f"  backend: {BACKEND}\n"
        repr_str += f"  device: {DEVICE}\n"
        # sequence settings
        repr_str += "Sequence/Task settings:\n"
        repr_str += f"  edge percentage: {EDGE_PERC}%\n"
        repr_str += f"  baseline duration: {BASELINE_DURATION} s\n"
        # detector settings
        repr_str += "Detector settings:\n"
        repr_str += f"  ECG height: {ECG_HEIGHT}\n"
        repr_str += f"  ECG distance: {ECG_DISTANCE}\n"
        repr_str += f"  ECG prominence: {ECG_PROMINENCE}\n"
        return repr_str

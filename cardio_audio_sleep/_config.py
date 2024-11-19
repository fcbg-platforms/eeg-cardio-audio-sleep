from __future__ import annotations

from pathlib import Path

# debugging recording
RECORDER: bool = False  # whether to record the buffer raw data
RECORDER_BUFSIZE: float = 300  # in seconds
RECORDER_PATH_RESPIRATION: Path = (
    Path.home() / "Documents" / "ras-data" / "debug-buffer-respiration-raw.fif"
)
RECORDER_PATH_CARDIAC: Path = (
    Path.home() / "Documents" / "ras-data" / "debug-buffer-cardiac-raw.fif"
)
TRG_CHANNEL: str = "TRIGGER"

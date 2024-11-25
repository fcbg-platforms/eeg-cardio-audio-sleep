from __future__ import annotations

from pathlib import Path

# debugging recording
RECORDER: bool = False  # whether to record the buffer raw data
RECORDER_BUFSIZE: float = 300  # in seconds
RECORDER_PATH: Path = Path.home() / "Documents" / "cas-data" / "debug-buffer-raw.fif"
TRG_CHANNEL: str = "TRIGGER"

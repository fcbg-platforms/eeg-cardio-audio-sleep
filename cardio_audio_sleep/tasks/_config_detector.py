from __future__ import annotations

# the peak detection is based on scipy.signal.find_peaks
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html
ECG_HEIGHT: float = 0.985
ECG_DISTANCE: float = 0.3
ECG_PROMINENCE: float | None = None

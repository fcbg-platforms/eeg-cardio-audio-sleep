from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from matplotlib import pyplot as plt

from .utils._checks import check_type
from .utils._docs import fill_doc

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


@fill_doc
class Viewer:
    """Viewer of a real-time cardiac signal with peak detection.

    Parameters
    ----------
    %(ecg_ch_name)s
    ecg_height : float
        The height of the ECG peaks as a percentage of the data range, between 0 and 1.
    """

    def __init__(self, ecg_ch_name: str, ecg_height: float) -> None:
        if plt.get_backend() != "QtAgg":
            plt.switch_backend("QtAgg")
        if not plt.isinteractive():
            plt.ion()  # enable interactive mode
        self._fig, self._axes = plt.subplots(1, 1, figsize=(8, 8))
        self._axes.set_title(f"ECG: {ecg_ch_name}")
        self._peaks = []
        self._ecg_height = ecg_height
        plt.show()

    @fill_doc
    def plot(self, ts: NDArray[np.float64], data: NDArray[np.float64]) -> None:
        """Plot the cardiac data and peaks.

        Parameters
        ----------
        ts : array of shape (n_samples,)
            Timestamps of the cardiac data.
        data : array of shape (n_samples,)
            Cardiac data.
        """
        assert ts.ndim == 1
        assert data.ndim == 1
        # prune peaks outside of the viewing window
        for k, peak in enumerate(self._peaks):
            if ts[0] <= peak:
                idx = k
                break
        else:
            idx = 0
        self._peaks = self._peaks[idx:]
        # update plotting window
        self._axes.clear()
        self._axes.plot(ts, data)
        for peak in self._peaks:
            self._axes.axvline(peak, color="red", linestyle="--")
        self._axes.axhline(
            np.percentile(data, self._ecg_height * 100), color="green", linestyle="--"
        )
        self._fig.canvas.draw()
        self._fig.canvas.flush_events()

    @fill_doc
    def add_peak(self, peak: float) -> None:
        """Add a peak to the viewer.

        Parameters
        ----------
        peak : float
            Timestamp of the peak.
        """
        check_type(peak, ("numeric",), "peak")
        assert 0 < peak
        self._peaks.append(peak)

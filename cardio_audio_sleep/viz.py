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
    """Viewer of a real-time respiration and/or cardiac signal with peak detection.

    Parameters
    ----------
    %(ecg_ch_name)s
    %(resp_ch_name)s
    ecg_height : float | None
        The height of the ECG peaks as a percentage of the data range, between 0 and 1.
    """

    def __init__(
        self,
        ecg_ch_name: str | None,
        resp_ch_name: str | None,
        ecg_height: float | None,
    ) -> None:
        if plt.get_backend() != "QtAgg":
            plt.switch_backend("QtAgg")
        if not plt.isinteractive():
            plt.ion()  # enable interactive mode
        picks = [elt for elt in (ecg_ch_name, resp_ch_name) if elt is not None]
        self._fig, axes = plt.subplots(len(picks), 1, figsize=(8, 8 * len(picks)))
        if ecg_ch_name is not None and resp_ch_name is not None:
            self._axes = {"ecg": axes[0], "resp": axes[1]}
            axes[0].set_title(f"ECG: {ecg_ch_name}")
            axes[1].set_title(f"Respiration: {resp_ch_name}")
        elif ecg_ch_name is not None:
            self._axes = {"ecg": axes}
            axes.set_title(f"ECG: {ecg_ch_name}")
        elif resp_ch_name is not None:
            self._axes = {"resp": axes}
            axes.set_title(f"Respiration: {resp_ch_name}")
        self._peaks = {"ecg": [], "resp": []}
        self._ecg_height = ecg_height
        plt.show()

    @fill_doc
    def plot(
        self, ts: NDArray[np.float64], data: NDArray[np.float64], ch_type: str
    ) -> None:
        """Plot the respiration or cardiac data and peaks.

        Parameters
        ----------
        ts : array of shape (n_samples,)
            Timestamps of the respiration data.
        data : array of shape (n_samples,)
            Respiration or cardiac data.
        %(ch_type)s
        """
        assert ts.ndim == 1
        assert data.ndim == 1
        # prune peaks outside of the viewing window
        for k, peak in enumerate(self._peaks[ch_type]):
            if ts[0] <= peak:
                idx = k
                break
        else:
            idx = 0
        self._peaks[ch_type] = self._peaks[ch_type][idx:]
        # update plotting window
        self._axes[ch_type].clear()
        self._axes[ch_type].plot(ts, data)
        for peak in self._peaks[ch_type]:
            self._axes[ch_type].axvline(peak, color="red", linestyle="--")
        if ch_type == "ecg":
            assert self._ecg_height is not None  # sanity-check
            self._axes[ch_type].axhline(
                np.percentile(data, self._ecg_height * 100),
                color="green",
                linestyle="--",
            )
        self._fig.canvas.draw()
        self._fig.canvas.flush_events()

    @fill_doc
    def add_peak(self, peak: float, ch_type: str) -> None:
        """Add a peak to the viewer.

        Parameters
        ----------
        peak : float
            Timestamp of the peak.
        %(ch_type)s
        """
        check_type(peak, ("numeric",), "peak")
        assert 0 < peak
        self._peaks[ch_type].append(peak)

"""MAtplotlib GUI to calibrate the peak detector settings."""

import math
import time
from itertools import cycle
from typing import Optional, Tuple

import numpy as np
from bsl import StreamReceiver
from matplotlib import pyplot as plt
from matplotlib.widgets import Button, Slider
from scipy.signal import find_peaks

from .utils import search_ANT_amplifier
from .utils._checks import _check_type, _check_value
from .utils._logs import logger


def peak_detection_parameters_tuning(
    ecg_ch_name: str,
    stream_name: Optional[str] = None,
    duration_buffer: float = 4.0,
) -> Tuple[float, Optional[float], Optional[float]]:
    """
    GUI to tune the height and width parameter of the R-peak detector.

    The GUI starts by acquiring 4 different buffer window that will be
    detrended and displayed.

    Parameters
    ----------
    ecg_ch_name : str
        Name of the ECG channel in the LSL stream.
    stream_name : str
        Name of the LSL stream to connect to. If None, attempts to find ANT
        amplifiers.
    duration_buffer : float
        The duration of the data buffer.

    Returns
    -------
    height : float
        The height setting retained (expressed as a percentage).
    prominence : float | None
        Minimum peak prominence as defined by scipy.
    width : float | None
        The width retained (expressed in ms)
    """
    data, fs = _acquire_data(ecg_ch_name, stream_name, duration_buffer)
    data = _detrend(data, duration_buffer)

    # ------------------------------------------------------------------------
    # Figure
    fig = plt.figure(figsize=(10, 10))

    # Data axis
    axs = list()
    for k in range(411, 415):
        axs.append(fig.add_subplot(k))
    fig.subplots_adjust(left=0.1, right=0.9, bottom=0.25)

    for k, ax in enumerate(axs):
        ax.plot(data[k], color="dimgray")

    # ------------------------------------------------------------------------
    # Slider for height percentile
    height_slider_ax = fig.add_axes(
        [0.1, 0.16, 0.6, 0.03], facecolor="lightgoldenrodyellow"
    )
    height_slider = Slider(height_slider_ax, "height", 80, 100.0, valinit=97.5)

    # Slider for prominence
    prominence_slider_ax = fig.add_axes([0.1, 0.13, 0.6, 0.03])
    prominence_slider = Slider(
        prominence_slider_ax, "prominence", 0, 2000, valinit=500.0
    )

    # Slider for width
    width_slider_ax = fig.add_axes(
        [0.1, 0.1, 0.6, 0.03], facecolor="lightgoldenrodyellow"
    )
    width_slider = Slider(width_slider_ax, "width", 0, 100, valinit=20.0)

    # Init lines
    global height_lines
    global peak_lines
    height_lines = _draw_height(axs, data, height_slider.val)
    peak_lines = _draw_peaks(
        axs,
        data,
        height_slider.val,
        prominence_slider.val,
        width_slider.val,
        fs,
    )

    # Action on slider change
    def sliders_on_changed(val):  # noqa: D401
        """Action on slider movement."""
        global height_lines
        global peak_lines
        global prominence_disabled
        global width_disabled

        # remove outdated height lines
        for k in range(len(height_lines) - 1, -1, -1):
            height_lines[-1].remove()
            del height_lines[-1]
        # remove outdated peak lines
        for peak_lines_ in peak_lines:
            for k in range(len(peak_lines_) - 1, -1, -1):
                peak_lines_[k].remove()
                del peak_lines_[k]

        # draw new lines
        height_lines = _draw_height(axs, data, height_slider.val)
        prominence = None if prominence_disabled else prominence_slider.val
        width = None if width_disabled else width_slider.val
        peak_lines = _draw_peaks(
            axs, data, height_slider.val, prominence, width, fs
        )

        # update fig
        fig.canvas.draw_idle()

    height_slider.on_changed(sliders_on_changed)
    width_slider.on_changed(sliders_on_changed)
    prominence_slider.on_changed(sliders_on_changed)

    # ------------------------------------------------------------------------
    global prominence_disabled
    global width_disabled
    prominence_disabled = False
    width_disabled = False

    # Button to disable prominence
    prominence_button_ax = fig.add_axes([0.8, 0.13, 0.1, 0.025])
    prominence_button = Button(
        prominence_button_ax,
        "Disable",
        color="lightgoldenrodyellow",
        hovercolor="0.975",
    )

    # Button to disable width
    width_button_ax = fig.add_axes([0.8, 0.1, 0.1, 0.025])
    width_button = Button(
        width_button_ax,
        "Disable",
        color="lightgoldenrodyellow",
        hovercolor="0.975",
    )

    prominence_colors = cycle(["0.975", "lightgoldenrodyellow"])
    prominence_hovercolors = cycle(["lightgoldenrodyellow", "0.975"])
    width_colors = cycle(["0.975", "lightgoldenrodyellow"])
    width_hovercolors = cycle(["lightgoldenrodyellow", "0.975"])

    def prominence_button_clicked(mouse_event):  # noqa: D401
        """Action on prominence button click."""
        global peak_lines
        global prominence_disabled
        global width_disabled
        prominence_disabled = not prominence_disabled
        # set colors
        prominence_button.color = next(prominence_colors)
        prominence_button.hovercolor = next(prominence_hovercolors)

        # remove outdated peak lines
        for peak_lines_ in peak_lines:
            for k in range(len(peak_lines_) - 1, -1, -1):
                peak_lines_[k].remove()
                del peak_lines_[k]

        # draw new lines
        prominence = None if prominence_disabled else prominence_slider.val
        width = None if width_disabled else width_slider.val
        peak_lines = _draw_peaks(
            axs, data, height_slider.val, prominence, width, fs
        )

        # update fig
        fig.canvas.draw_idle()

    def width_button_clicked(mouse_event):  # noqa: D401
        """Action on width button click."""
        global peak_lines
        global prominence_disabled
        global width_disabled
        width_disabled = not width_disabled
        # set colors
        width_button.color = next(width_colors)
        width_button.hovercolor = next(width_hovercolors)

        # remove outdated peak lines
        for peak_lines_ in peak_lines:
            for k in range(len(peak_lines_) - 1, -1, -1):
                peak_lines_[k].remove()
                del peak_lines_[k]

        # draw new lines
        prominence = None if prominence_disabled else prominence_slider.val
        width = None if width_disabled else width_slider.val
        peak_lines = _draw_peaks(
            axs, data, height_slider.val, prominence, width, fs
        )

        # update fig
        fig.canvas.draw_idle()

    prominence_button.on_clicked(prominence_button_clicked)
    width_button.on_clicked(width_button_clicked)

    # ------------------------------------------------------------------------
    # Add a reset button
    reset_button_ax = fig.add_axes([0.68, 0.025, 0.1, 0.04])
    reset_button = Button(
        reset_button_ax,
        "Reset",
        color="lightgoldenrodyellow",
        hovercolor="0.975",
    )

    def reset_button_on_clicked(mouse_event):
        height_slider.reset()
        prominence_slider.reset()
        width_slider.reset()

    reset_button.on_clicked(reset_button_on_clicked)

    # ------------------------------------------------------------------------
    # Add a confirm button
    confirm_button_ax = fig.add_axes([0.8, 0.025, 0.1, 0.04])
    confirm_button = Button(
        confirm_button_ax,
        "Confirm",
        color="lightgoldenrodyellow",
        hovercolor="0.975",
    )

    def confirm_button_on_clicked(mouse_event):
        plt.close(fig=fig)

    confirm_button.on_clicked(confirm_button_on_clicked)

    # ------------------------------------------------------------------------
    # Show
    plt.show(block=True)

    # Retrieve values
    height = height_slider.val
    prominence = None if prominence_disabled else prominence_slider.val
    width = None if width_disabled else width_slider.val

    return height, prominence, width


def _acquire_data(ecg_ch_name, stream_name, duration_buffer):
    """Acquire data for plot from LSL stream."""
    _check_type(ecg_ch_name, (str,), item_name="ecg_ch_name")
    _check_type(stream_name, (str, None), item_name="stream_name")
    _check_type(duration_buffer, ("numeric",), item_name="duration_buffer")
    if stream_name is None:
        stream_name = search_ANT_amplifier()
    if duration_buffer <= 0.2:
        raise ValueError(
            "Argument 'duration_buffer' must be strictly larger than 0.2. "
            f"Provided: '{duration_buffer}' seconds."
        )
    sr = StreamReceiver(bufsize=duration_buffer, stream_name=stream_name)
    if len(sr.streams) == 0:
        raise ValueError("The StreamReceiver did not connect to any streams.")
    _check_value(
        ecg_ch_name, sr.streams[stream_name].ch_list, item_name="ecg_ch_name"
    )
    ecg_ch_idx = sr.streams[stream_name].ch_list.index(ecg_ch_name)

    # Acquisition
    logger.info("Starting data acquisition for tuning..")
    time.sleep(0.5)
    data = list()
    for k in range(4):
        logger.info(
            "%i/4: Waiting %ss to fill the buffer..", k + 1, duration_buffer
        )
        time.sleep(duration_buffer + 0.2)
        sr.acquire()
        data_, _ = sr.get_buffer()
        data.append(data_[:, ecg_ch_idx])
        time.sleep(2.5)
        logger.info("%i/4 complete!", k + 1)

    # Retrieve sampling rate
    fs = sr.streams[stream_name].sample_rate

    return data, fs


def _detrend(data, duration_buffer):
    """Apply detrending to the data."""
    for k, data_ in enumerate(data):
        times = np.linspace(0, duration_buffer, data_.size)
        z = np.polyfit(times, data_, 1)
        linear_fit = z[0] * times + z[1]
        data[k] = data_ - linear_fit

    return data


def _draw_peaks(axs, data, height, prominence, width, fs):
    """Draw the peaks vertical lines on all 4 axis."""
    peak_lines = [[] * 4]
    for k, ax in enumerate(axs):
        height_ = np.percentile(data[k], height)
        width = math.ceil(width / 1000 * fs) if width is not None else None
        peaks, _ = find_peaks(
            data[k], height=height_, prominence=prominence, width=width
        )
        peak_lines.append([])  # init new list
        for peak in peaks:
            peak_lines[-1].append(
                ax.axvline(peak, linestyle="--", color="navy", linewidth=0.75)
            )

    return peak_lines


def _draw_height(axs, data, height):
    """Draw the vertical lines corresponding to the height on all 4 axis."""
    height_lines = list()
    for k, ax in enumerate(axs):
        height_ = np.percentile(data[k], height)
        height_lines.append(ax.axhline(height_, linestyle="--", color="tan"))

    return height_lines

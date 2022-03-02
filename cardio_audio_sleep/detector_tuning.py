import time

from bsl import StreamReceiver
from matplotlib import pyplot as plt
from matplotlib.widgets import Button, Slider
import numpy as np
from mne.filter import filter_data
from scipy.signal import find_peaks

from . import logger
from .utils import search_ANT_amplifier
from .utils._checks import _check_type, _check_value


def peak_detection_parameters_tuning(
        ecg_ch_name: str,
        stream_name: str = None,
        duration_buffer: float = 4
        ):
    """
    GUI to tune the height parameter of the R-peak detector.

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
        The height setting retained (express as a percentage).
    """
    _check_type(ecg_ch_name, (str, ), item_name='ecg_ch_name')
    _check_type(stream_name, (str, None), item_name='stream_name')
    _check_type(duration_buffer, ('numeric', ),
                item_name='duration_buffer')
    if stream_name is None:
        stream_name = search_ANT_amplifier()
    if duration_buffer <= 0.2:
        raise ValueError(
            "Argument 'duration_buffer' must be strictly larger than 0.2. "
            f"Provided: '{duration_buffer}' seconds.")
    sr = StreamReceiver(bufsize=duration_buffer, stream_name=stream_name)
    if len(sr.streams) == 0:
        raise ValueError(
            'The StreamReceiver did not connect to any streams.')
    _check_value(ecg_ch_name, sr.streams[stream_name].ch_list,
                 item_name='ecg_ch_name')
    ecg_ch_idx = sr.streams[stream_name].ch_list.index(ecg_ch_name)

    # Acquisition
    logger.info('Starting data acquisition for tuning..')
    time.sleep(0.5)
    data = list()
    for k in range(4):
        logger.info('%i/4: Waiting %ss to fill the buffer..',
                    k+1, duration_buffer)
        time.sleep(duration_buffer + 0.2)
        sr.acquire()
        data_, _ = sr.get_buffer()
        data.append(data_[:, ecg_ch_idx])
        time.sleep(2.5)
        logger.info('%i/4 complete!', k+1)

    # Retrive sampling rate
    fs = sr.streams[stream_name].sample_rate

    # Clean-up
    del sr
    del data_

    # Filter
    for k, data_ in enumerate(data):
        data[k] = filter_data(data_, fs, 1., 15., phase='zero')

    # Figure
    fig = plt.figure(figsize=(10, 10))

    # Data axis
    axs = list()
    for k in range(411, 415):
        axs.append(fig.add_subplot(k))
    fig.subplots_adjust(left=0.1, right=0.9, bottom=0.25)

    for k, ax in enumerate(axs):
        ax.plot(data[k], color='dimgray')

    # Slider for height percentile
    height_slider_ax = fig.add_axes([0.1, 0.15, 0.8, 0.03],
                                    facecolor='lightgoldenrodyellow')
    height_slider = Slider(height_slider_ax, 'height', 80, 100., valinit=97.5)

    # Init lines
    global height_lines
    global peak_lines
    height_lines = _draw_height(axs, data, height_slider)
    peak_lines = _draw_peaks(axs, data, height_slider)

    # Action on slider change
    def sliders_on_changed(val):
        """Action on slider movement."""
        global height_lines
        global peak_lines

        # remove outdated height lines
        for k in range(len(height_lines)-1, -1, -1):
            height_lines[-1].remove()
            del height_lines[-1]
        # remove outdated peak lines
        for peak_lines_ in peak_lines:
            for k in range(len(peak_lines_)-1, -1, -1):
                peak_lines_[k].remove()
                del peak_lines_[k]

        # draw new lines
        height_lines = _draw_height(axs, data, height_slider)
        peak_lines = _draw_peaks(axs, data, height_slider)

        # update fig
        fig.canvas.draw_idle()
    height_slider.on_changed(sliders_on_changed)

    # Add a reset buttom
    reset_button_ax = fig.add_axes([0.68, 0.025, 0.1, 0.04])
    reset_button = Button(reset_button_ax, 'Reset',
                          color='lightgoldenrodyellow',
                          hovercolor='0.975')

    def reset_button_on_clicked(mouse_event):
        height_slider.reset()
    reset_button.on_clicked(reset_button_on_clicked)

    # Add a confirm button
    confirm_button_ax = fig.add_axes([0.8, 0.025, 0.1, 0.04])
    confirm_button = Button(confirm_button_ax, 'Confirm',
                            color='lightgoldenrodyellow',
                            hovercolor='0.975')

    def confirm_button_on_clicked(mouse_event):
        plt.close(fig=fig)
    confirm_button.on_clicked(confirm_button_on_clicked)

    # Show
    plt.show(block=True)

    return height_slider.val


def _draw_peaks(axs, data, height_slider):
    """Draw the peaks vertical lines on all 4 axis."""
    peak_lines = [[] * 4]
    for k, ax in enumerate(axs):
        height = np.percentile(data[k], height_slider.val)
        peaks, _ = find_peaks(data[k], height=height)
        peak_lines.append([])  # init new list
        for peak in peaks:
            peak_lines[-1].append(
                ax.axvline(peak, linestyle='--', color='navy', linewidth=0.75))

    return peak_lines


def _draw_height(axs, data, height_slider):
    """Draw the vertical lines corresponding to the height on all 4 axis."""
    height_lines = list()
    for k, ax in enumerate(axs):
        height = np.percentile(data[k], height_slider.val)
        height_lines.append(ax.axhline(height, linestyle='--', color='tan'))

    return height_lines

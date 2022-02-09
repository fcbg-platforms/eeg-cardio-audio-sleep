import time

from bsl import StreamReceiver
from matplotlib import pyplot as plt
from matplotlib.widgets import Button, Slider
import numpy as np
from scipy.signal import find_peaks

from . import logger
from .utils._checks import _check_type, _check_value


def peak_detection_parameters_tuning(
        stream_name: str,
        ecg_ch_name: str,
        duration_buffer: float = 5
        ):
    """
    GUI to tune the height and the prominence parameter of the R-peak detector.

    The GUI starts by acquiring 4 different buffer window that will be
    detrended and displayed.

    Parameters
    ----------
    stream_name : str
        Name of the LSL stream to connect to.
    ecg_ch_name : str
        Name of the ECG channel in the LSL stream.
    duration_buffer : float
        The duration of the data buffer.

    Returns
    -------
    height : float
        The height setting retained (express as a percentage).
    prominence : float
        The prominence setting retained.
    """
    _check_type(stream_name, (str, ), item_name='stream_name')
    _check_type(ecg_ch_name, (str, ), item_name='ecg_ch_name')
    _check_type(duration_buffer, ('numeric', ),
                item_name='duration_buffer')
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

    # Clean-up
    del sr
    del data_

    # Detrending
    for k, data_ in enumerate(data):
        times = np.linspace(0, duration_buffer, data_.size)
        z = np.polyfit(times, data_, 1)
        linear_fit = z[0] * times + z[1]
        data[k] = data_ - linear_fit

    # Figure
    fig = plt.figure(figsize=(10, 10))

    # Data axis
    axs = list()
    for k in range(411, 415):
        axs.append(fig.add_subplot(k))
    fig.subplots_adjust(left=0.1, right=0.9, bottom=0.25)

    for k in range(4):
        axs[k].plot(data[k], color='dimgray')

    # Slider for height percentile
    height_slider_ax  = fig.add_axes([0.1, 0.15, 0.8, 0.03],
                                     facecolor='lightgoldenrodyellow')
    height_slider = Slider(height_slider_ax, 'height', 80, 100., valinit=98.)

    for k in range(4):
        axs[k].axhline(np.percentile(data[k], height_slider.val),
                       linestyle='--', color='tan')

    # Slider for prominence
    prominence_slider_ax  = fig.add_axes([0.1, 0.1, 0.8, 0.03],
                                     facecolor='lightgoldenrodyellow')
    prominence_slider = Slider(prominence_slider_ax, 'prominence',
                               100, 4000, valinit=700.)

    for k in range(4):
        peaks, _ = find_peaks(data[k],
                              height=np.percentile(data[k], height_slider.val),
                              prominence=prominence_slider.val)
        for peak in peaks:
            axs[k].axvline(peak, linestyle='--', color='navy', linewidth=0.75)

    # Action on slider change
    def sliders_on_changed(val):
        # replot data
        for k in range(4):
            axs[k].clear()
            axs[k].plot(data[k], color='dimgray')

        # recompute height / prominence
        height=np.percentile(data[k], height_slider.val)
        prominence=prominence_slider.val

        # add height lines
        for k in range(4):
            axs[k].axhline(height, linestyle='--', color='tan')

        # add peaks
        for k in range(4):
            peaks, _ = find_peaks(
                data[k], height=height, prominence=prominence)
            for peak in peaks:
                axs[k].axvline(peak, linestyle='--', color='navy',
                               linewidth=0.75)

        # update fig
        fig.canvas.draw_idle()
    height_slider.on_changed(sliders_on_changed)
    prominence_slider.on_changed(sliders_on_changed)

    # Add a reset buttom
    reset_button_ax = fig.add_axes([0.68, 0.025, 0.1, 0.04])
    reset_button = Button(reset_button_ax, 'Reset',
                          color='lightgoldenrodyellow',
                          hovercolor='0.975')
    def reset_button_on_clicked(mouse_event):
        height_slider.reset()
        prominence_slider.reset()
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
    plt.show(block = True)

    return height_slider.val, prominence_slider.val

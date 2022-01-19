import time

from bsl import StreamRecorder, StreamPlayer
from bsl.utils import Timer
from bsl.triggers.software import TriggerSoftware
from mne import find_events
from mne.io import read_raw_fif
from matplotlib import pyplot as plt
from neurokit2.ecg import ecg_findpeaks
from scipy.signal import butter, sosfiltfilt

from cardio_audio_sleep import Detector


if __name__ == '__main__':  # required on windows PC for multiprocessing
#%% Start a Mock StreamPlayer
    fif = 'C:/Users/Mathieu/Documents/git/cardio-audio-sleep/data/ecg-raw.fif'
    sp = StreamPlayer('StreamPlayer', fif)
    sp.start(blocking=True)

    #%% Initialize
    recorder = StreamRecorder('C:/Users/Mathieu/Downloads/', fname='test',
                              fif_subdir=False)
    recorder.start()
    time.sleep(0.2)
    trigger = TriggerSoftware(recorder)
    detector = Detector('StreamPlayer', 'ECG')  # takes 5 seconds to init
    timer = Timer()

    #%% Record
    trigger.signal(2)  # start trigger

    while timer.sec() <= 60:
        time.sleep(0.1)  # don't update too often to pull more than 1 chunk
        detector.update_loop()
        peak, pos = detector.new_peaks()
        if peak:
            trigger.signal(1)  # trigger when the peak was found
            # audio/trigger should be schedule based on pos

    trigger.signal(2)
    time.sleep(0.5)
    trigger.close()
    time.sleep(0.5)
    recorder.stop()

    #%% Stop Mock StreamPlayer
    sp.stop()

    #%% Load file and plot
    fname = 'C:/Users/Mathieu/Downloads/test-StreamPlayer-raw.fif'
    raw = read_raw_fif(fname, preload=True)
    events = find_events(raw, stim_channel='TRIGGER')

    # Retrieve data array
    data = raw.get_data(picks='ECG')[0, :]

    # BP filter
    bp_low = 1 / (0.5 * raw.info['sfreq'])
    bp_high = 15 / (0.5 * raw.info['sfreq'])
    sos = butter(1, [bp_low, bp_high], btype='bandpass', output='sos')
    clean = sosfiltfilt(sos, data)
    peaks = ecg_findpeaks(clean, sampling_rate=raw.info['sfreq'],
                          method='kalidas2017')

    # Plot
    f, ax = plt.subplots(1, 1)
    ax.plot(raw.times, clean)
    for ev in events:
        if ev[2] == 1:
            ax.axvline(raw.times[ev[0]], color='yellow')
        if ev[2] == 2:
            ax.axvline(raw.times[ev[0]], color='crimson', linewidth=3)
    for peak in peaks['ECG_R_Peaks']:
        ax.axvline(raw.times[peak], color='teal', linestyle='--')

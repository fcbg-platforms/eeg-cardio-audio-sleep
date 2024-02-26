from byte_trigger import ParallelPortTrigger

from cardio_audio_sleep import Detector
from cardio_audio_sleep.utils import search_ANT_amplifier

# %% Triggers
trigger = ParallelPortTrigger("/dev/parport0")

# %% LSL Streams
stream_name = search_ANT_amplifier()
ecg_ch_name = "AUX7"

# %% Peak detection
peak_height_perc = 97.5  # %
peak_prominence = 500
peak_width = None  # ms | None
n = 30

# %% Loop
detector = Detector(
    stream_name,
    ecg_ch_name,
    duration_buffer=4,
    peak_height_perc=peak_height_perc,
    peak_prominence=peak_prominence,
    peak_width=peak_width,
)
detector.prefill_buffer()

counter = 0
while counter <= n:
    detector.update_loop()
    pos = detector.new_peaks()
    if pos is not None:
        trigger.signal(1)
        counter += 1

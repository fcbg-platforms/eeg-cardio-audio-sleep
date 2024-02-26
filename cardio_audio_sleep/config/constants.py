from warnings import warn

# PsychoPy windows constants
SCREEN_SIZE = (1920, 1080)
SCREEN_KWARGS = dict(
    size=SCREEN_SIZE,
    winType="pyglet",
    monitor=None,
    screen=1,
    fullscr=True,
    allowGUI=False,
)
# Pure tone stimuli
TONE_FQ = 1000  # Hz


# Trigger definitions
class TriggerDef(dict):
    def __getattr__(self, key):
        if key in self:
            warn(
                "Triggers are exposed as dictionary keys. Attribute access is "
                "deprecated.",
                DeprecationWarning,
                stacklevel=2,
            )
            return self[key]
        else:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{key}'."
            )


TRIGGERS: dict[str, int] = TriggerDef(
    sound=16,
    omission=32,
    percussion=48,
    string=64,
    wind=80,
    sync_start=96,
    sync_stop=112,
    iso_start=128,
    iso_stop=144,
    async_start=160,
    async_stop=176,
    baseline_start=192,
    baseline_stop=208,
    pause=224,
    resume=240,
)

TRIGGER_HWD: dict[str, int] = TriggerDef(
    percussion=1,
    string=2,
    wind=4,
    extra=8,
)

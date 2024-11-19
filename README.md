[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![codecov](https://codecov.io/gh/fcbg-platforms/eeg-resp-audio-sleep/graph/badge.svg?token=nalw3f1s1X)](https://codecov.io/gh/fcbg-platforms/eeg-resp-audio-sleep)
[![tests](https://github.com/fcbg-platforms/eeg-resp-audio-sleep/actions/workflows/pytest.yaml/badge.svg?branch=main)](https://github.com/fcbg-platforms/eeg-resp-audio-sleep/actions/workflows/pytest.yaml)

# Resp-Audio-Sleep study

Project to study sound stimulus synchronous, asynchronous and isochronous with
the respiration during sleep.

## Install

### Operating System

Recommended OS: Ubuntu 22.04 LTS or 24.04 LTS, generic kernel.

> [!Tip]
> On Ubuntu 24.04 LTS, Wayland is the default display server and replaces X11. In
> theory, it should be more performant and have lower latencies than X11. In practice,
> the stimulation software (PsychoPy, psychtoolbox, ...) and the rendering software
> (pyvistaqt, ...) don't support Wayland well yet which can lead to crash or unexpected
> behaviors / latencies.

### Python installation

- Add the deadsnake PPA and install python 3.10 (current version supported by PsychoPy).

  ```bash
  $ sudo add-apt-repository ppa:deadsnakes/ppa
  $ sudo apt update
  $ sudo apt install python3.10 python3.10-venv
  ```

- Prevent installations without virtual environment (optional, good practice).

  ```bash
  $ sudo apt install nano  # if absent from the system
  $ nano ~/.profile
  ```

  Add the lines:

  ```
  PYTHONNOUSERSITE=1
  PIP_REQUIRE_VIRTUALENV=1
  ```

- Clone the project and create an environment.

  ```bash
  $ cd ~
  $ mkdir git
  $ git clone https://github.com/fcbg-platforms/eeg-resp-audio-sleep
  ```

> [!Tip]
> I recommend you install [VSCode](https://code.visualstudio.com/Download) and use it to
> spawn the terminal with an activated environment. In VSCode, `File` -> `OpenFolder`
> then open the `~/git/eeg-resp-audio-sleep` folder just cloned, `Ctrl+Shift+P` ->
> `Create New Terminal`.

- Create a virtual environment.

  ```bash
  $ cd ~/git/eeg-resp-audio-sleep  # if not in VSCode
  $ python3.10 -m venv .venv --copies
  ```

> [!Tip]
> If you are using VSCode, a pop-up on the bottom right detects the new environment
> and ask if it should be the default environment for this folder. Select `Yes`, you
> will not always have this environment activated in VSCode when you open the folder
> `~/git/eeg-resp-audio-sleep`.

### PsychoPy preparation

- Retrieve the wxPython wheel for your platform [here](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/) (ubuntu only, wheels are available for the other OS).

> [!Tip]
> If you run Ubuntu 24.04 LTS, or if you want, you can build the wheel from source. Run
> `pip install wxPython`, and resolve successively the displayed errors by installing
> the missing libraries/compilers. The build takes a couple of minutes.

- Install dependencies

  ```bash
  $ sudo apt install libusb-1.0-0-dev portaudio19-dev libasound2-dev libsdl2-2.0-0
  ```

- Edit ulimits

  ```bash
  $ sudo groupadd --force psychopy
  $ sudo usermod -aG psychopy $USER  # replace with your username
  $ sudo nano /etc/security/limits.d/99-psychopylimits.conf
  ```

  Set the content to:

  ```
  @psychopy   -  nice       -20
  @psychopy   -  rtprio     50
  @psychopy   -  memlock    unlimited
  ```

### Install the project

> [!Tip]
> Install `uv` first as it's faster than `pip`.

From within the created virtual environment:

```bash
$ pip install uv
$ pip install stimuli --ignore-requires-python
$ cd ~/git/eeg-resp-audio-sleep  # not in this directory already
$ uv pip install -e .[all]
```

> [!IMPORTANT]
> Note that we install `stimuli` first with the flag `--ignore-requires-python` because
> `stimuli` requires python 3.11 and above while `PsychoPy` requires python 3.10
> maximum. The version pin on `stimuli` is due to limitation on Windows and does not
> impact performance on Linux, thus it is safe to ignore the version pin.

> [!IMPORTANT]
> Note the `-e` flag used for an editable install. As the configuration files are within
> the package, this flag must be used for changes to take effect. It's also handy to
> use this flag in-case you need to update the package from source, im which case a
> simple `git pull` will suffice.

Install also the additional `ipython` and `ipykernel` packages if you are in VSCode, as
they are useful especially for interactive windows.

```bash
$ uv pip install ipython ipykernel
```

## Usage

### Command-line interface

The paradigm is controlled by command-line from the activated environment.

> [!Tip]
> If you use VSCode, the environment will always be activated provided that your
> workspace is set to `eeg-resp-audio-sleep`, i.e. thjat you opened the folder
> `~/git/eeg-resp-audio-sleep`.

In the terminal, enter:

```bash
$ ras
```

It will display all the available commands, for instance `test-sequence`, with an
associated description. To get help on a specific command and on its argument, enter the
pattern:

```bash
$ ras COMMAND --help
```

For instance:

```bash
$ ras test-sequence --help
```

> [!TIP]
> Every time a command is invoked, the current configuration is displayed, including
> the type of trigger, the sound settings, the detection settings, ...

The arguments of a command can be entered following this pattern:

```bash
$ ras COMMAND ARG1 VALUE1 ARG2 VALUE2
```

For instance:

```bash
$  ras test-sequence --target 440 --deviant 1000
```

> [!TIP]
> Some argument might accept more than 1 value, in which case the pattern becomes
> `ras COMMAND ARG1 VALUE1_1 VALUE1_2 ARG2 VALUE2` and some argument might only control
> a boolean flag, in this case the pattern becomes `ras COMMAND ARG`.

Note that every mandatory argument will be requested in the terminal if it was absent
from the command. Note that some arguments can only be provided as part of the initial
command.

### Configuration

The configuration of the triggers, sound, sequence, ... is done in the file
`~/git/eeg-resp-audio-sleep/resp_audio_sleep/tasks/_config.py`.

Important variables:
- The variable `TARGET_DELAY` controls how long after a peak the sound should be
  delivered.
- The variable `N_TARGET` and `N_DEVIANT` control how many target and deviant are
  present in the sequence.
- The variable `TRIGGERS` controls both which trigger is delivered for which sound, but
  also which sound frequency is available. As of now, the `target` value of a task can
  be set to `1000`, `2000`, `440` and the `deviant` value of a task can be set to
  `1000` and `2000`.

The configuration of the detector settings is done in the file
`~/git/eeg-resp-audio-sleep/resp_audio_sleep/tasks/_config_detector.py`.

### Note about the detector testing

The cardiac and respiration detectors can be tested with the commands
`test-detector-cardiac` and `test-detector-respiration`. In both case, a real-time
visualization of the internal buffer and of the peak detection is displayed. In the
terminal, a log of the time it took to detect the last peak is displayed. This time
might seem excessive. This is due to the visualization slowing down the online loop
tremendously. If you want to estimate the time it takes to detect a peak, you can run
those commands with the `--no-viewer` flag which disables visualization. The timings in
the console should now be reasonable.

```bash
$ ras test-detector-respiration --stream STREAM --ch-name-resp AUX7 --n-peaks 20 --no-viewer
```

## Timing measurements

In `script/conversion-fif.py`, you have a conversion script from XDF to FIFF.
In `script/timings.py`, you have a parsing and timing measurement script which uses the
FIFF files. The script is organized as a notebook file with `# %%` defined cells. In
VSCode, you can run an entire cell at once.

> [!IMPORTANT]
> Make sure to modify the path at which it will search for the files. By default, it
> takes the files in `data/` which have been measured at Campus Biotech.

Pay attention to the channels for the synchronous condition and for the audio
measurements (jack to touchproof). For now, the channels are set as:

- AUX7: Cardiac
- AUX8: Respiration
- AUX9: Audio

> [!IMPORTANT]
> Make sure to disable deviant sounds with `N_DEVIANT=0` and to use a target sound which
> can be sampled, e.g. `440` Hz.

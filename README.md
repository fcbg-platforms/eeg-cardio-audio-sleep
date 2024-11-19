[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![codecov](https://codecov.io/gh/fcbg-platforms/eeg-cardio-audio-sleep/graph/badge.svg?token=0C2HBV5GSM)](https://codecov.io/gh/fcbg-platforms/eeg-cardio-audio-sleep)
[![tests](https://github.com/fcbg-platforms/eeg-cardio-audio-sleep/actions/workflows/pytest.yaml/badge.svg?branch=main)](https://github.com/fcbg-platforms/eeg-cardio-audio-sleep/actions/workflows/pytest.yaml)

# Cardio-Audio-Sleep study

Project to study sound stimulus synchronous, asynchronous and isochronous with
the heartbeat during sleep.

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
  $ git clone https://github.com/fcbg-platforms/eeg-cardio-audio-sleep
  ```

> [!Tip]
> I recommend you install [VSCode](https://code.visualstudio.com/Download) and use it to
> spawn the terminal with an activated environment. In VSCode, `File` -> `OpenFolder`
> then open the `~/git/eeg-cardio-audio-sleep` folder just cloned, `Ctrl+Shift+P` ->
> `Create New Terminal`.

- Create a virtual environment.

  ```bash
  $ cd ~/git/eeg-cardio-audio-sleep  # if not in VSCode
  $ python3.10 -m venv .venv --copies
  ```

> [!Tip]
> If you are using VSCode, a pop-up on the bottom right detects the new environment
> and ask if it should be the default environment for this folder. Select `Yes`, you
> will not always have this environment activated in VSCode when you open the folder
> `~/git/eeg-cardio-audio-sleep`.

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
$ cd ~/git/eeg-cardio-audio-sleep  # not in this directory already
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
> workspace is set to `eeg-cardio-audio-sleep`, i.e. that you opened the folder
> `~/git/eeg-cardio-audio-sleep`.

In the terminal, enter:

```bash
$ cas
```

It will display all the available commands, for instance `test-sequence`, with an
associated description. To get help on a specific command and on its argument, enter the
pattern:

```bash
$ cas COMMAND --help
```

For instance:

```bash
$ cas test-sequence --help
```

> [!TIP]
> Every time a command is invoked, the current configuration is displayed, including
> the type of trigger, the sound settings, the detection settings, ...

The arguments of a command can be entered following this pattern:

```bash
$ cas COMMAND ARG1 VALUE1 ARG2 VALUE2
```

For instance:

```bash
$  cas test-sequence --verbose debug
```

> [!TIP]
> Some argument might accept more than 1 value, in which case the pattern becomes
> `cas COMMAND ARG1 VALUE1_1 VALUE1_2 ARG2 VALUE2` and some argument might only control
> a boolean flag, in this case the pattern becomes `cas COMMAND ARG`.

Note that every mandatory argument will be requested in the terminal if it was absent
from the command. Note that some arguments can only be provided as part of the initial
command.

### Configuration

The configuration of the triggers, sound, sequence, ... is done in the file
`~/git/eeg-cardio-audio-sleep/cardio_audio_sleep/tasks/_config.py`.

Important variables:
- The variable `TARGET_DELAY` controls how long after a peak the sound should be
  delivered.
- The variable `N_SOUND` and `N_OMISSION` control how many sound and omission are
  present in the sequence.
- The variable `TRIGGERS` controls both which trigger is delivered for a sound and for
  an omission.

The configuration of the detector settings is done in the file
`~/git/eeg-cardio-audio-sleep/cardio_audio_sleep/tasks/_config_detector.py`.

### Note about the detector testing

The cardiac detector can be tested with the commands `test-detector`. It creates a
real-time visualization of the internal buffer and of the peak detection. In the
terminal, a log of the time it took to detect the last peak is displayed. This time
might seem excessive. This is due to the visualization slowing down the online loop
tremendously. If you want to estimate the time it takes to detect a peak, you can run
those commands with the `--no-viewer` flag which disables visualization. The timings in
the console should now be reasonable.

```bash
$ cas test-detector --stream STREAM --ch-name-ecg AUX7 --n-peaks 20 --no-viewer
```

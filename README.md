[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)


# Cardio-Audio-Sleep study

Project to study sound stimulus synchronous, asynchronous and isochronous with
the heartbeat during sleep.

# Install instructions

This package can be installed with `pip install .` or
`python setup.py install` after cloning the repository locally.

This package requires [PsychoPy](https://www.psychopy.org/). The installation
instructions can be found [here](https://www.psychopy.org/download.html).

On Linux, PsychToolbox requires the following libraries:

```
sudo apt-get install libusb-1.0-0-dev portaudio19-dev libasound2-dev libsdl2-2.0-0
```

For EyeLink eye-tracking, `pylink` is required. The wheel should be retrieved
from [SR Research](https://www.sr-research.com/).

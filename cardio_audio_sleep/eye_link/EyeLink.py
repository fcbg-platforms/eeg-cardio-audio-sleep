from __future__ import division, print_function

import os
from pathlib import Path

import pylink
from psychopy import core, event, logging, monitors, visual

from .. import logger
from .._typing import EYELink
from ..utils._checks import _check_type
from . import EyeLinkCoreGraphicsPsychoPy

# set psychopy log level
logging.console.setLevel(logging.CRITICAL)


class Eyelink(EYELink):
    def __init__(self, pname="./", fname="TEST"):
        # Set this variable to True to run the script in "Dummy Mode"
        dummy_mode = False
        # Set this variable to True to run the task in full screen mode
        # It is easier to debug the script in non-fullscreen mode
        full_screen = True
        host_ip = "100.1.1.1"
        # Set up EDF data file name and local data folder
        # The EDF data filename should not exceed 8 alphanumeric characters
        # use ONLY number 0-9, letters, & _ (underscore) in the filename
        pname = Path(_check_type(pname, ("path-like",), "pname"))
        if not pname.exists():
            os.makedirs(pname)
        self.edf_pname = pname
        fname = _check_type(fname, (str,), "fname")
        if fname.endswith(".EDF"):
            fname = fname.split(".EDF")[0]
        if 8 < len(fname):
            raise ValueError(
                "The fname should not exceed 8 alphanumeric characters."
            )
        self.edf_fname = fname

        # ----------------------------------------------------------------------
        # Step 1: Connect to the EyeLink Host PC
        #
        # The Host IP address, by default, is "100.1.1.1".
        # the "el_tracker" objected created here can be accessed through Pylink
        # Set the Host PC address to "None" (without quotes) to run the script
        # in "Dummy Mode"
        if dummy_mode:
            self.el_tracker = pylink.EyeLink(None)
        else:
            try:
                self.el_tracker = pylink.EyeLink(host_ip)
            except RuntimeError:
                self.close()
                raise

        # -------------------------------------------------------------------
        # Step 2: Open an EDF data file on the Host PC
        try:
            self.el_tracker.openDataFile(self.edf_fname + ".EDF")
        except RuntimeError:
            self.close()
            raise

        # -------------------------------------------------------------------
        # Step 3: Configure the tracker
        # Put the tracker in offline mode before we change tracking parameters
        self.el_tracker.setOfflineMode()

        # Get the software version:
        # 1-EyeLink I, 2-EyeLink II, 3/4-EyeLink 1000, 5-EyeLink 1000 Plus,
        # 6-Portable DUO
        eyelink_ver = 0  # set version to 0, in case running in Dummy mode
        if not dummy_mode:
            vstr = self.el_tracker.getTrackerVersionString()
            eyelink_ver = int(vstr.split()[-1].split(".")[0])
            logger.debug(
                "Running experiment on %s, version %d", (vstr, eyelink_ver)
            )

        # File and Link data control
        # -> what eye events to save in the EDF file?
        # -> include everything by default
        file_event_flags = (
            "LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON,INPUT"
        )
        # -> what eye events to make available over the link?
        # -> include everything by default
        link_event_flags = (
            "LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON,FIXUPDATE,INPUT"
        )
        # what sample data to save in the EDF data file and to make available
        # over the link, include the 'HTARGET' flag to save head target sticker
        # data for supported eye trackers.
        if eyelink_ver > 3:
            file_sample_flags = (
                "LEFT,RIGHT,GAZE,HREF,RAW,AREA,HTARGET,"
                + "GAZERES,BUTTON,STATUS,INPUT"
            )
            link_sample_flags = (
                "LEFT,RIGHT,GAZE,GAZERES,AREA,HTARGET,STATUS,INPUT"
            )
        else:
            file_sample_flags = (
                "LEFT,RIGHT,GAZE,HREF,RAW,AREA,GAZERES,BUTTON,STATUS,INPUT"
            )
            link_sample_flags = "LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS,INPUT"

        self.el_tracker.sendCommand(f"file_event_filter = {file_event_flags}")
        self.el_tracker.sendCommand(f"file_sample_data = {file_sample_flags}")
        self.el_tracker.sendCommand(f"link_event_filter = {link_event_flags}")
        self.el_tracker.sendCommand(f"link_sample_data = {link_sample_flags}")

        # Optional tracking parameters
        # Sample rate, 250, 500, 1000, or 2000, c.f. tracker specification
        # if eyelink_ver > 2:
        #     el_tracker.sendCommand("sample_rate 1000")
        # Choose a calibration type, H3, HV3, HV5, HV13
        # (HV = horizontal/vertical)
        self.el_tracker.sendCommand("calibration_type = HV9")
        # Set a gamepad button to accept calibration/drift check target
        # You need a supported gamepad/button box that is connected to the
        # Host PC
        self.el_tracker.sendCommand(
            "button_function 5 'accept_target_fixation'"
        )

        # Step 4: set up a graphics environment for calibration
        # Open a window, be sure to specify monitor parameters
        mon = monitors.Monitor("myMonitor", width=53.0, distance=70.0)
        self.win = visual.Window(
            fullscr=full_screen,
            monitor=mon,
            winType="pyglet",
            units="pix",
            screen=1,
        )

        # get the native screen resolution used by PsychoPy
        self.scn_width, self.scn_height = self.win.size

        # Pass the display pixel coordinates (left, top, right, bottom) to the
        # tracker, c.f. EyeLink Installation Guide "Customizing Screen Settings"
        el_coords = (
            "screen_pixel_coords = 0 0 "
            + f"{self.scn_width - 1} {self.scn_height - 1}"
        )
        self.el_tracker.sendCommand(el_coords)

        # Configure a graphics environment (genv) for tracker calibration
        self.genv = EyeLinkCoreGraphicsPsychoPy(self.el_tracker, self.win)
        logger.debug(self.genv)  # version number of the CoreGraphics library

        # Set background and foreground colors for the calibration target
        # in PsychoPy, (-1, -1, -1)=black, (1, 1, 1)=white, (0, 0, 0)=mid-gray
        foreground_color = (-1, -1, -1)
        background_color = self.win.color
        self.genv.setCalibrationColors(foreground_color, background_color)
        self.genv.setTargetType("circle")
        self.genv.setTargetSize(24)
        pylink.openGraphicsEx(self.genv)

    # ----------------------------
    def clear_screen(self):
        """clear up the PsychoPy window"""
        self.win.fillColor = self.genv.getBackgroundColor()
        self.win.flip()

    def show_msg(self, text, wait_for_keypress=True):
        """Show task instructions on screen"""
        msg = visual.TextStim(
            self.win,
            text,
            color=self.genv.getForegroundColor(),
            wrapWidth=self.scn_width / 2,
        )
        self.clear_screen()
        msg.draw()
        self.win.flip()

        # wait indefinitely, terminates upon any key press
        if wait_for_keypress:
            event.waitKeys()
            self.clear_screen()

    # Step 5: Set up the camera and calibrate the tracker
    def calibrate_el(self):
        # Show the task instructions
        task_msg = "\nPress ENTER twice to display tracker menu"
        self.show_msg(task_msg)
        try:
            self.el_tracker.doTrackerSetup()
        except RuntimeError:
            self.el_tracker.exitCalibration()
            self.close()
            raise

    def start_recording_el(self):
        self.el_tracker.startRecording(1, 1, 1, 1)
        self.el_tracker.sendMessage("START")

    def stop_recording_el(self):
        self.el_tracker.stopRecording()
        self.el_tracker.setOfflineMode()

        # Clear the Host PC screen and wait for 500 ms
        self.el_tracker.sendCommand("clear_screen 0")
        pylink.msecDelay(500)

        # Close the edf data file on the Host
        self.el_tracker.closeDataFile()
        # Download the EDF data file from the Host PC to a local data folder
        # parameters: source_file_on_the_host, destination_file_on_local_drive
        local_edf = self.edf_pname / (self.edf_fname + ".EDF")
        try:
            self.el_tracker.receiveDataFile(self.edf_fname + ".EDF", local_edf)
        except RuntimeError:
            self.close()
            raise

        # Close the link to the tracker.
        self.el_tracker.close()
        # close the PsychoPy window
        self.win.close()
        # quit PsychoPy
        core.quit()

    def close(self):
        """Close in case a RuntimeError was raised."""
        try:
            self.el_tracker.close()
        except Exception:
            pass
        try:
            self.win.close()
        except Exception:
            pass
        try:
            core.quit()
        except Exception:
            pass

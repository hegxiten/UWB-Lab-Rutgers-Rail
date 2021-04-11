#!/usr/bin/python3

import os, platform, sys, json

import serial, glob, re
import time

import subprocess, atexit, signal

import threading, queue

from utils import *
from tft import RangingGUI

from tkinter import *
from tkinter import ttk
from tkinter import font

from functools import partial

# NOTE: When RPi cannot connect to the slaves (serial port init failed), turn the UWB on and off using Android a couple times
# NOTE: When some slaves cannot be ranged with by masters, power it off and turn it on back again (unplug the cord).

# The firmware on DWM1001-Dev devices is updated to dwm-acceleromter-enabled.
# Therefore the reporting pattern has been changed from the OEM. 
# To use shell mode on masters, it needs to either 
#   1) turn off the location engine (LE), or: 
#   2) set a very low positioning update rate 
# in order to avoid constant reporting, which is not yet stoppable otherwise.
# The reporting will compromise shell commands/outputs.
# Useful shell commands: 
# "aurs <active> <stationary>": 
#       can be used to slow down/speed up the update rate;
# "acts <meas_mode><accel_en><low_pwr><loc_en><leds><ble><uwb><fw_upd><sec>" 
#       can be used to turn on/off location engine

def on_exit(serialport, verbose=False):
    """ On exit callbacks to make sure the serialport is closed when
        the program ends.
    """
    if verbose:
        sys.stdout.write(timestamp_log() + "Serial port {} closed on exit\n".format(serialport.port))
    if sys.platform.startswith('linux'):
        import fcntl
        fcntl.flock(serialport, fcntl.LOCK_UN)
    serialport.close()
        

def config_uart_settings(serial_port, settings):
    pass


def main():
    dirname = os.path.dirname(__file__)    
    try:
        # ----------- Init GUI display if there is a screen ----------- 
        # ----------- UI interactions are available to control ranging within GUI -----------
        # ----------- Controls are from GUI buttons, not here -----------
        gui_root = Tk()
        gui = RangingGUI(root=gui_root, parent=gui_root)
        gui.root.mainloop()
    except:
        # ---- there is no peripheral display to support GUI -----
        # ---- Run ranging automatically at background -----
        serial_ports = pairing_uwb_ports(init_reporting=True)
        q = queue.LifoQueue()
        end_ranging_thread = threading.Thread(  target=end_ranging_job_both_sides_synced, 
                                                args=(serial_ports, q,),
                                                name="End Reporting Thread",
                                                daemon=True)
        end_ranging_thread.start()
        while True:
            pass
        end_ranging_thread.join()


if __name__ == "__main__":
    main()
    
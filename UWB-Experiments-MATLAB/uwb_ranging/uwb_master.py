#!/usr/bin/python3

import os, sys

import threading, queue

from utils import *
from ranging_gui import RangingGUI

from tkinter import *

if sys.platform.startswith('darwin'):
    USERDIR = os.path.join("/Users")
    USERNAME = os.environ.get('LOGNAME')
if sys.platform.startswith('linux'):
    USERDIR = os.path.join("/home")
    USERNAME = os.environ.get('USER')
if sys.platform.startswith('win'):
    USERDIR = os.path.join("C:/", "Users")
    USERNAME = os.getlogin()
os.makedirs(os.path.join(USERDIR, USERNAME, "uwb_ranging"), exist_ok=True)


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
    """ Dynamically configure the UWB devices using UART serial port according to
        application needs. Reserved. 
    """
    pass


def main():
    dirname = os.path.dirname(__file__)    
    try:
        # ----------- Init GUI display if there is a screen ----------- 
        # ---- UI interactions are available to control ranging within GUI ----
        # ----------- Controls are from GUI buttons, not here -----------
        gui_root = Tk()
        gui = RangingGUI(root=gui_root, parent=gui_root)
        gui.set_user_dir(USERDIR)
        gui.set_user_name(USERNAME)
        gui.root.mainloop()
        gui.root.update()
    except TclError as e:
        # ---- there is no peripheral display to support GUI -----
        # ---- Run ranging automatically at background -----
        serial_ports = {}
        pairing_uwb_ports(init_reporting=True, serial_ports_dict=serial_ports)
        A_END_CODE, B_END_CODE = 2, 1
        q_a_end, q_b_end = queue.LifoQueue(), queue.LifoQueue()
        a_end_ranging_thread = threading.Thread(target=end_ranging_job_async_single,
                                                kwargs={"serial_ports": serial_ports, 
                                                        "end_side_code": A_END_CODE,
                                                        "data_ptr_queue_single_end": q_a_end,
                                                        "log_fpath": os.path.join(USERDIR, USERNAME, "uwb_ranging"),
                                                        "exp_name": timestamp_log(shorten=True)},
                                                name="A End Reporting Thread Async",
                                                daemon=True)
        b_end_ranging_thread = threading.Thread(target=end_ranging_job_async_single,
                                                kwargs={"serial_ports": serial_ports, 
                                                        "end_side_code": B_END_CODE,
                                                        "data_ptr_queue_single_end": q_b_end,
                                                        "log_fpath": os.path.join(USERDIR, USERNAME, "uwb_ranging"),
                                                        "exp_name": timestamp_log(shorten=True)},
                                                name="B End Reporting Thread Async",
                                                daemon=True)
        a_end_ranging_thread.start()
        b_end_ranging_thread.start()
        
        while True:
            pass


if __name__ == "__main__":
    main()
    
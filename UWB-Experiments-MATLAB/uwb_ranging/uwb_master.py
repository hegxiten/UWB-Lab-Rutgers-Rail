#!/usr/bin/python3

import os, platform, sys, json

import serial, glob, re
import time

import subprocess, atexit, signal

import threading, queue

from utils import *
from tft import *

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


def parse_uart_init(serial_port, oem_firmware=False, pause_reporting=True):
    # Overwrite the util function with the same name 
    # register the callback functions when the service ends
    # atexit for regular exit, signal.signal for system kills
    try:
        atexit.register(on_exit, serial_port, True)
        signal.signal(signal.SIGTERM, on_killed)
        # Double enter (carriage return) as specified by Decawave shell
        # Extra delay is required to switch to shell mode. Insufficient delay will fail. 
        serial_port.reset_input_buffer()
        # 0.5 seconds between each "Enter" type is necessary. 
        # Too fast typing (e.g. 0.2 sec) will fail
        write_shell_command(serial_port, command=b'\x0D\x0D', delay=0.5) 
        if oem_firmware:
            if is_reporting_loc(serial_port):
                if pause_reporting:
                    # By default the update rate is 10Hz/100ms. Check again for data flow
                    # If data is flowing, stop the data flow (temporarily) to execute commands
                    write_shell_command(serial_port, command=b'\x6C\x65\x63\x0D', delay=0.2)
                return True
            return True # 03272021 Debug: Force it True to see if can turn on anchor's serial ports or not
            if serial_port.in_waiting > 0:
                return True
        else:
            # Type "av" command to config/init accelerometer
            # If accelerometer is not configured/init, acceleration will get wrong values
            write_shell_command(serial_port, command=b'\x61\x76\x0D', delay=0.2) 
            if is_reporting_loc(serial_port):            
                if pause_reporting:
                    # Write "aurs 600 600" to slow down reporting into 60s/ea. (pause data reporting)
                    write_shell_command(serial_port, command=b'\x61\x75\x72\x73\x20\x36\x30\x30\x20\x36\x30\x30\x0D', delay=0.2)
                sys.stdout.write(timestamp_log() + "Serial port {} init success\n".format(serial_port.name))
                return True
            return True # 03272021 Debug: Force it True to see if can turn on anchor's serial ports or not
            if serial_port.in_waiting > 0:
                return True
    except:
        sys.stdout.write(timestamp_log() + "Serial port {} init failed\n".format(serial_port.name))
        raise BaseException("SerialPortInitFailed")
        

def pairing_uwb_ports(oem_firmware=False, init_reporting=True):
    serial_tty_devices = [os.path.join("/dev", i) for i in os.listdir("/dev/") if "ttyACM" in i]
    serial_ports = {}
    # Match the serial ports with the device list    
    for dev in serial_tty_devices:
        try:
            p = serial.Serial(dev, baudrate=115200, timeout=3.0)
        except:
            continue
        port_available_check(p)
        # Initialize the UART shell command
        if parse_uart_init(p):
            sys_info = parse_uart_sys_info(p, verbose=True)
            uwb_addr_short = sys_info.get("addr")[-4:]
            # Link the individual Master/Slave with the serial ports by hashmap
            serial_ports[uwb_addr_short] = {}
            serial_ports[uwb_addr_short]["port"] = p
            serial_ports[uwb_addr_short]["sys_info"] = sys_info
            if "an" in sys_info["uwb_mode"]:
                serial_ports[uwb_addr_short]["config"] = "slave"
                serial_ports[uwb_addr_short]["info_pos"] = {}
                # here we temporarily set slave end side unknown to its hosting vehicle.
                # TODO: encode slave info position into its label let its hosting vehicle know its informative position.
                # TODO: slaves are having a hard time initialization (serial port ttyACMx, and one out of multiple times it will fail.)
                # TODO: restructure the initialization and speed it up (currently it takes too long to initialize.)
                # TODO: Maybe later we can close the ports linking to the Slave/Anchors if no needs
                # TODO: (03272021) The needs to open slave/anchor ports are: determine local slaves or foreign slaves. 
                # TODO: (03272021) Find a way around if slave serial ports cannot be opened (by discovery on 03272021). 
                

            elif "tn" in sys_info["uwb_mode"]: 
                serial_ports[uwb_addr_short]["config"] = "master"
                master_info_dict = decode_info_pos_from_label(sys_info["label"])
                master_info_dict["master_id"] = uwb_addr_short
                serial_ports[uwb_addr_short]["info_pos"] = master_info_dict
                if init_reporting:
                    if oem_firmware:
                        if not is_reporting_loc(p):
                            # Type "lec\n" to the dwm shell console to activate data reporting
                            write_shell_command(p, command=b'\x6C\x65\x63\x0D', delay=0.2)
                    else:
                        # Write "aurs 1 1" to speed up data reporting into 0.1s/ea. (resume data reporting)
                        write_shell_command(p, command=b'\x61\x75\x72\x73\x20\x31\x20\x31\x0D', delay=0.2)
                    assert is_reporting_loc(p)

            else:
                raise("unknown master/slave configuration!")
            
    return serial_ports

def config_uart_settings(serial_port, settings):
    pass


def end_ranging_job(serial_ports, master_dev_ids, data_ptrs_queue, masters_info_pos, oem_firmware=False):
    master_dev_a_id, master_dev_b_id = master_dev_ids[0], master_dev_ids[1]
    data_pointer_a_end, data_pointer_b_end = [{}, []], [{}, []]
    a_master_info_pos, b_master_info_pos = masters_info_pos[0], masters_info_pos[1]

    port_a_master, port_b_master = serial_ports[master_dev_a_id].get("port"), serial_ports[master_dev_b_id].get("port")
    
    atexit.register(on_exit, port_a_master, True)
    atexit.register(on_exit, port_b_master, True)

    if not is_reporting_loc(port_a_master):
        if oem_firmware:
            # Type "lec\n" to the dwm shell console to activate data reporting
            write_shell_command(port_a_master, command=b'\x6C\x65\x63\x0D', delay=0.2) 
        else:
            # Write "aurs 1 1" to speed up data reporting into 0.1s/ea.
            write_shell_command(port_a_master, command=b'\x61\x75\x72\x73\x20\x31\x20\x31\x0D', delay=0.2)
        
    if not is_reporting_loc(port_b_master):        
        if oem_firmware:
            # Type "lec\n" to the dwm shell console to activate data reporting
            write_shell_command(port_b_master, command=b'\x6C\x65\x63\x0D', delay=0.2) 
        else:
            # Write "aurs 1 1" to speed up data reporting into 0.1s/ea.
            write_shell_command(port_b_master, command=b'\x61\x75\x72\x73\x20\x31\x20\x31\x0D', delay=0.2)
    
    assert is_reporting_loc(port_a_master)
    assert is_reporting_loc(port_b_master)
    
    super_frame_a, super_frame_b = 0, 0
    port_a_master.reset_input_buffer()
    port_b_master.reset_input_buffer()

    while True:
        try:
            data_a = str(port_a_master.readline(), encoding="UTF-8").rstrip()
            data_b = str(port_b_master.readline(), encoding="UTF-8").rstrip()
            if not data_a[:4] == "DIST" or not data_b[:4] == "DIST":
                continue
            if oem_firmware:
                uwb_reporting_dict_a, uwb_reporting_dict_b = make_json_dict_oem(data_a), make_json_dict_oem(data_b)
            else:
                uwb_reporting_dict_a, uwb_reporting_dict_b = make_json_dict_accel_en(data_a), make_json_dict_accel_en(data_b)
            
            slave_reporting_dict_a, slave_reporting_dict_b = decode_slave_info_position(uwb_reporting_dict_a), decode_slave_info_position(uwb_reporting_dict_b)
            uwb_reporting_dict_a['superFrameNumber'], uwb_reporting_dict_b['superFrameNumber'] = super_frame_a, super_frame_b
            
            ranging_results_foreign_slaves_from_a_end_master, ranging_results_foreign_slaves_from_b_end_master = [], []
            for anc in uwb_reporting_dict_a.get("all_anc_id", []):
                if not serial_ports.get(anc):
                    # If the anchor/slave id is not recognized, it is from foreign vehicle (filter out local slaves). 
                    ranging_results_foreign_slaves_from_a_end_master.append(slave_reporting_dict_a.get(anc, {}))
            for anc in uwb_reporting_dict_b.get("all_anc_id", []):
                if not serial_ports.get(anc):
                    # If the anchor/slave id is not recognized, it is from foreign vehicle (filter out local slaves).
                    ranging_results_foreign_slaves_from_b_end_master.append(slave_reporting_dict_b.get(anc, {}))
            
            # Sort by proximity - nearest first
            ranging_results_foreign_slaves_from_a_end_master.sort(key=lambda x: x.get("dist_to", float("inf")))
            ranging_results_foreign_slaves_from_b_end_master.sort(key=lambda x: x.get("dist_to", float("inf")))
            # TODO: in case of Internet/WLAN access, considering publishing the data through MQTT
            # Write/publish data
            # json_data_a, json_data_b = json.dumps(uwb_reporting_dict_a), json.dumps(uwb_reporting_dict_b)
            # tag_client.publish("Tag/{}/Uplink/Location".format(tag_id[-4:]), json_data, qos=0, retain=True)
            data_pointer_a_end[0] = uwb_reporting_dict_a
            data_pointer_a_end[1] = process_raw_ranging_results(ranging_results_foreign_slaves_from_a_end_master,
                                                                ranging_results_foreign_slaves_from_b_end_master,
                                                                a_master_info_pos,
                                                                b_master_info_pos)
            super_frame_a += 1

            data_pointer_b_end[0] = uwb_reporting_dict_b
            data_pointer_b_end[1] = process_raw_ranging_results(ranging_results_foreign_slaves_from_b_end_master,
                                                                ranging_results_foreign_slaves_from_a_end_master,
                                                                b_master_info_pos,
                                                                a_master_info_pos)
            super_frame_b += 1

            data_ptrs_queue.put([data_pointer_a_end, data_pointer_b_end])
             
    
            # wait for new UWB reporting results
            # ------------ report into logs every 5 sec ------------ #
            if int(time.time() % 5) == 0:
                if data_pointer_a_end[1]:
                    sys.stdout.write(timestamp_log() + "A end reporting: " + repr(data_pointer_a_end[1]) + "\n")
                if data_pointer_b_end[1]:
                    sys.stdout.write(timestamp_log() + "B end reporting: " + repr(data_pointer_b_end[1]) + "\n")

        except Exception as exp:
            data_a = str(port_a_master.readline(), encoding="UTF-8").rstrip()
            data_b = str(port_b_master.readline(), encoding="UTF-8").rstrip()
            sys.stdout.write(timestamp_log() + "End reporting thread failed. Last fetched UART data: A: {}; B: {}. Thread: {}\n"
                             .format(data_a, data_b, threading.current_thread().getName()))
            raise exp
            sys.exit()


def main():
    dirname = os.path.dirname(__file__)
    vehicles = {} # the hashmap of all vehicles, self and others
    vehicle = [] # the list of other vehicles to range with
    
    # Identify the Master devices and their ends
    # Pair the serial ports (/dev/ttyACM*) with the individual UWB transceivers, get a hashmap keyed by UWB IDs
    # TODO: Warning mechanism development.
    # TODO: Display initialization and necessary program status on to the GUI.
    serial_ports = pairing_uwb_ports(init_reporting=True)
    
    a_end_master, b_end_master = "", ""
    for dev in serial_ports:
        if serial_ports[dev]["config"] == "master":
            if serial_ports[dev]["info_pos"].get("side_master") == 2:
                a_end_master = dev
                a_end_master_info_pos = serial_ports[dev]["info_pos"]
            if serial_ports[dev]["info_pos"].get("side_master") == 1:
                b_end_master = dev
                b_end_master_info_pos = serial_ports[dev]["info_pos"]
        elif serial_ports[dev]["config"] == "slave":
            if serial_ports[dev]["info_pos"].get("side_slave") == 2:
                a_end_slave = dev
                a_end_slave_info_pos = serial_ports[dev]["info_pos"]
            if serial_ports[dev]["info_pos"].get("side_slave") == 1:
                b_end_slave = dev
                b_end_slave_info_pos = serial_ports[dev]["info_pos"]
        else:
            continue

    q = queue.Queue()
    end_ranging_thread = threading.Thread(  target=end_ranging_job, 
                                            args=(serial_ports,
                                                (a_end_master, b_end_master),
                                                q,
                                                (a_end_master_info_pos, b_end_master_info_pos)),
                                            name="End Reporting Thread",
                                            daemon=True)
    

    # ----------- Start of Future Refactoring ----------- 
    
    gui = RangingPlotterGUI(q=q)
    end_ranging_thread.start()
    gui.root.mainloop()

    end_ranging_thread.join()


if __name__ == "__main__":
    main()
    
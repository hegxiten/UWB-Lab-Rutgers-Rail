

import os, platform, sys, json

import serial, glob, re
import time

import subprocess, atexit, signal

import threading

from utils import *
from lcd import *

# On 02.28.2021: update note:
# The firmware on DWM1001-Dev devices is updated to dwm-acceleromter-enabled.
# The reporting pattern is changed. To use shell mode on masters, it needs to either 1) turn off the location engine (LE)
# or: 2) set a very low positioning update rate in order to avoid constant reporting, which is not yet stoppable otherwise.
# The reporting will compromise shell commands/outputs.
# shell command "aurs <active> <stationary>" can be used to slow down/speed up the positioning update rate;
# shell commadn "acts <meas_mode><accel_en><low_pwr><loc_en><leds><ble><uwb><fw_upd><sec>" can be used to
# turn on/off location engine

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
        write_shell_command(serial_port, command=b'\x0D\x0D', delay=0.5)
        if oem_firmware:
            if is_reporting_loc(serial_port):
                if pause_reporting:
                    # By default the update rate is 10Hz/100ms. Check again for data flow
                    # If data is flowing, stop the data flow (temporarily) to execute commands
                    write_shell_command(serial_port, command=b'\x6C\x65\x63\x0D')
            return True
        else:
            # Type "av" command to config/init accelerometer
            # If accelerometer is not configured/init, acceleration will get wrong values
            write_shell_command(serial_port, command=b'\x61\x76\x0D') 
            if is_reporting_loc(serial_port):            
                if pause_reporting:
                    # Write "aurs 600 600" to slow down reporting into 60s/ea. (pause data reporting)
                    write_shell_command(serial_port, command=b'\x61\x75\x72\x73\x20\x36\x30\x30\x20\x36\x30\x30\x0D')
                sys.stdout.write(timestamp_log() + "Serial port {} init success\n".format(serial_port.name))
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
            sys_info = parse_uart_sys_info(p)
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
                
            elif "tn" in sys_info["uwb_mode"]: 
                serial_ports[uwb_addr_short]["config"] = "master"
                serial_ports[uwb_addr_short]["info_pos"] = parse_info_position_from_label(sys_info["label"])
                
            else:
                raise("unknown master/slave configuration!")
            if init_reporting:
                if oem_firmware:
                    if not is_reporting_loc(p):
                        # Type "lec\n" to the dwm shell console to activate data reporting
                        if dev == a_end_master or dev == b_end_master:
                            write_shell_command(p, command=b'\x6C\x65\x63\x0D')
                else:
                    # Write "aurs 1 1" to speed up data reporting into 0.1s/ea. (resume data reporting)
                    write_shell_command(p, command=b'\x61\x75\x72\x73\x20\x31\x20\x31\x0D')
                assert is_reporting_loc(p)
                # TODO: Maybe later we can close the ports linking to the Slave/Anchors if no needs
    return serial_ports

def config_uart_settings(serial_port, settings):
    pass


def end_ranging_thread_job(serial_ports, devs, data_ptrs, masters_info_pos, oem_firmware=False):
    dev_a, dev_b = devs[0], devs[1]
    data_pointer_a_end, data_pointer_b_end = data_ptrs[0], data_ptrs[1]
    a_master_info_pos, b_master_info_pos = masters_info_pos[0], masters_info_pos[1]
    
    port_a_info_dict, port_b_info_dict = serial_ports.get(dev_a), serial_ports.get(dev_b)
    port_a, port_b = port_a_info_dict.get("port"), port_b_info_dict.get("port")
    sys_info_a, sys_info_b = port_a_info_dict.get("sys_info"), port_b_info_dict.get("sys_info")
    
    atexit.register(on_exit, port_a, True)
    atexit.register(on_exit, port_b, True)

    if not is_reporting_loc(port_a):
        if oem_firmware:
            # Type "lec\n" to the dwm shell console to activate data reporting
            write_shell_command(port_a, command=b'\x6C\x65\x63\x0D') 
        else:
            # Write "aurs 1 1" to speed up data reporting into 0.1s/ea.
            write_shell_command(port_a, command=b'\x61\x75\x72\x73\x20\x31\x20\x31\x0D')
        
    if not is_reporting_loc(port_b):        
        if oem_firmware:
            # Type "lec\n" to the dwm shell console to activate data reporting
            write_shell_command(port_b, command=b'\x6C\x65\x63\x0D') 
        else:
            # Write "aurs 1 1" to speed up data reporting into 0.1s/ea.
            write_shell_command(port_b, command=b'\x61\x75\x72\x73\x20\x31\x20\x31\x0D')
    
    assert is_reporting_loc(port_a)
    assert is_reporting_loc(port_b)
    
    super_frame_a, super_frame_b = 0, 0
    port_a.reset_input_buffer()
    port_b.reset_input_buffer()

    while True:
        try:
            data_a = str(port_a.readline(), encoding="UTF-8").rstrip()
            data_b = str(port_b.readline(), encoding="UTF-8").rstrip()
            if not data_a[:4] == "DIST" or not data_b[:4] == "DIST":
                continue
            if oem_firmware:
                uwb_reporting_dict_a, uwb_reporting_dict_b = make_json_dict_oem(data_a), make_json_dict_oem(data_b)
            else:
                uwb_reporting_dict_a, uwb_reporting_dict_b = make_json_dict_accel_en(data_a), make_json_dict_accel_en(data_b)
            
            slave_reporting_dict_a, slave_reporting_dict_b = decode_slave_info_position(uwb_reporting_dict_a), decode_slave_info_position(uwb_reporting_dict_b)
            uwb_reporting_dict_a['superFrameNumber'], uwb_reporting_dict_b['superFrameNumber'] = super_frame_a, super_frame_b
            
            ranging_results_a, ranging_results_b = [], []
            for anc in uwb_reporting_dict_a.get("all_anc_id", []):
                if not serial_ports.get(anc):
                    # If the anchor/slave id is not recognized, it is from foreign vehicle.
                    ranging_results_a.append((anc, slave_reporting_dict_a.get(anc, {})))
            for anc in uwb_reporting_dict_b.get("all_anc_id", []):
                if not serial_ports.get(anc):
                    # If the anchor/slave id is not recognized, it is from foreign vehicle.
                    ranging_results_b.append((anc, slave_reporting_dict_b.get(anc, {})))
            
            # Sort by proximity - nearest first
            ranging_results_a.sort(key=lambda x: x[1].get("dist_to", float("inf")))
            ranging_results_b.sort(key=lambda x: x[1].get("dist_to", float("inf")))
            # Write/publish data
            json_data_a, json_data_b = json.dumps(uwb_reporting_dict_a), json.dumps(uwb_reporting_dict_b)
            # tag_client.publish("Tag/{}/Uplink/Location".format(tag_id[-4:]), json_data, qos=0, retain=True)
            data_pointer_a_end[0], data_pointer_a_end[1] = uwb_reporting_dict_a, calculate_adjusted_dist(ranging_results_a, a_master_info_pos)
            data_pointer_b_end[0], data_pointer_b_end[1] = uwb_reporting_dict_b, calculate_adjusted_dist(ranging_results_b, b_master_info_pos)
            super_frame_a += 1
            super_frame_b += 1
             
        except Exception as exp:
            data_a = str(port_a.readline(), encoding="UTF-8").rstrip()
            data_b = str(port_b.readline(), encoding="UTF-8").rstrip()
            sys.stdout.write(timestamp_log() + "End reporting thread failed. Last fetched UART data: A: {}; B: {}. Thread: {}\n"
                             .format(data_a, data_b, threading.currentThread().getName()))
            raise exp
            sys.exit()


if __name__ == "__main__":
    dirname = os.path.dirname(__file__)
    vehicles = {} # the hashmap of all vehicles, self and others
    vehicle = [] # the list of other vehicles to range with
    
    # Identify the Master devices and their ends
    # Pair the serial ports (/dev/ttyACM*) with the individual UWB transceivers, get a hashmap keyed by UWB IDs
    serial_ports = pairing_uwb_ports(init_reporting=True)
    
    a_end_master, b_end_master = "", ""
    for dev in serial_ports:
        if serial_ports[dev]["info_pos"].get("side_master") == "A" and "tn" in serial_ports[dev]["sys_info"]["uwb_mode"]:
            a_end_master = dev
            a_end_master_info_pos = serial_ports[dev]["info_pos"]
        if serial_ports[dev]["info_pos"].get("side_master") == "B" and "tn" in serial_ports[dev]["sys_info"]["uwb_mode"]:
            b_end_master = dev
            b_end_master_info_pos = serial_ports[dev]["info_pos"]
    
    a_end_ranging_res_ptr, b_end_ranging_res_ptr = [{}, []], [{}, []]
    end_ranging_thread = threading.Thread(target=end_ranging_thread_job, 
                                            args=(serial_ports,
                                                  (a_end_master, b_end_master),
                                                  (a_end_ranging_res_ptr, b_end_ranging_res_ptr),
                                                  (a_end_master_info_pos, b_end_master_info_pos)),
                                            name="A End Ranging",
                                            daemon=True)
    
    lcd_init()
    end_ranging_thread.start()
    
    while True:
        # wait for new UWB reporting results
        stt = time.time()
        if a_end_ranging_res_ptr[1]:
            sys.stdout.write("A end reporting: " + repr(a_end_ranging_res_ptr[1]) + "\n")
        if b_end_ranging_res_ptr[1]:
            sys.stdout.write("B end reporting: " + repr(b_end_ranging_res_ptr[1]) + "\n")
        
        line1 = "A:{} {}".format(a_end_ranging_res_ptr[1][0][0], round(a_end_ranging_res_ptr[1][0][1]["adjusted_dist"],1)) if a_end_ranging_res_ptr[1] else "A End OutOfRange"
        line2 = "B:{} {}".format(b_end_ranging_res_ptr[1][0][0], round(b_end_ranging_res_ptr[1][0][1]["adjusted_dist"],1)) if b_end_ranging_res_ptr[1] else "B End OutOfRange"
        lcd_disp(line1, line2)
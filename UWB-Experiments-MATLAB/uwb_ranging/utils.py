from datetime import datetime
from collections import defaultdict
import sys, time, json, re, base64, math, os, threading
import serial, serial.tools.list_ports
import atexit, signal


def load_config_json(json_path):
    raise("loading json is deprecated! ")


def timestamp_log(incl_UTC=False, brackets=True, shorten=False):
    """ Get the timestamp for the stdout log message
        
        :returns:
            string format local timestamp with option to include UTC 
    """
    if shorten:
        return str(datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    if brackets:
        local_timestp = "["+str(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))+" local] "
        utc_timestp = "["+str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))+" UTC] "
    else:
        local_timestp = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))+" local "
        utc_timestp = str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))+" UTC "
    if incl_UTC:
        return local_timestp + utc_timestp
    else:
        return local_timestp    


def write_shell_command(serial_port, command, delay=0.1):
    """ Function wrapper to properly write shell commands into DWM1001-Dev with delay 
        Delay is necessary for successful command input. 
        
        :returns:
            None
    """
    if serial_port.is_open:
        time.sleep(delay)
        for B in command:
            serial_port.write(bytes([B]))
            time.sleep(delay)


def on_exit(serial_port, verbose=False):
    """ On exit callbacks to make sure the serial port is closed when
        the program ends.
    """
    if verbose:
        sys.stdout.write(timestamp_log() + "Serial port {} closed on exit\n".format(serial_port.name))
    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        import fcntl
        fcntl.flock(serial_port, fcntl.LOCK_UN)
    serial_port.close()


def on_killed(serial_port, signum, frame):
    """ Closure function as handler to signal.signal in order to pass serial port name
    """
    # if killed by UNIX, no need to execute on_exit callback
    atexit.unregister(on_exit)
    sys.stdout.write(timestamp_log() + "Serial port {} closed on killed\n".format(serial_port.name))
    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        import fcntl
        fcntl.flock(serial_port, fcntl.LOCK_UN)
    serial_port.close()


def serial_port_available_check_flock(serial_port):
    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        import fcntl
        try:
            fcntl.flock(serial_port, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, BlockingIOError) as exp:
            sys.stdout.write(timestamp_log() + "Serial port {} is busy. Another process is accessing the port. \n".format(serial_port.name))
            raise exp
    else:
        sys.stdout.write(timestamp_log() + "Serial port {} is ready.\n".format(serial_port.name))


def is_uwb_shell_ok(serial_port, verbose=False):
    """ Detect if the DWM1001 Tag's shell console is responding to \x0D\x0D
        
        :returns:
            True or False
    """
    serial_port.reset_input_buffer()
    write_shell_command(serial_port, command=b'\x0D\x0D', delay=0.2)
    if serial_port.in_waiting:
        return True
    return False


def is_reporting_loc(serial_port, timeout=1, verbose=False):
    """ Detect if the DWM1001 Tag is running on data reporting mode
        
        :returns:
            True or False
    """
    if serial_port.is_open:
        serial_port.reset_input_buffer()
        init_bytes_avail = serial_port.in_waiting
        time.sleep(timeout)
        final_bytes_avail = serial_port.in_waiting
        if final_bytes_avail - init_bytes_avail > 0:
            if verbose:
                sys.stdout.write(timestamp_log() + "Serial port {} reporting check: input buffer of {} second(s) is {}\n"
                                .format(serial_port.name, timeout, str(serial_port.read(serial_port.in_waiting))))
            return True
    return False


def serial_port_uart_init(serial_port, oem_firmware=False, pause_reporting=True):
    # Overwrite the util function with the same name 
    # register the callback functions when the service ends
    # atexit for regular exit, signal.signal for system kills
    try:
        # atexit.register(on_exit, serial_port, True)
        # signal.signal(signal.SIGTERM, on_killed)
        # Double enter (carriage return) as specified by Decawave shell
        # Extra delay is required to switch to shell mode. Insufficient delay will fail. 
        serial_port.reset_input_buffer()
        # 0.5 seconds between each "Enter" type is necessary. 
        # Too fast typing (e.g. 0.2 sec) will fail
        write_shell_command(serial_port, command=b'\x0D\x0D', delay=0.2)
        if oem_firmware:
            if pause_reporting:
                # By default the update rate is 10Hz/100ms. Check again for data flow
                # If data is flowing, stop the data flow (temporarily) to execute commands
                write_shell_command(serial_port, command=b'\x6C\x65\x63\x0D', delay=0.2)
            return True # 03272021 Debug: Force it True to see if can turn on anchor's serial ports or not
        else:
            # Type "av" command to config/init accelerometer
            # If accelerometer is not configured/init, acceleration will get wrong values
            write_shell_command(serial_port, command=b'\x61\x76\x0D', delay=0.2) 
            if pause_reporting:
                # Write "aurs 600 600" to slow down reporting into 60s/ea. (pause data reporting)
                write_shell_command(serial_port, command=b'\x61\x75\x72\x73\x20\x36\x30\x30\x20\x36\x30\x30\x0D', delay=0.2)
            sys.stdout.write(timestamp_log() + "Serial port {} init success\n".format(serial_port.name))
            return True
    except:
        sys.stdout.write(timestamp_log() + "Serial port {} init failed\n".format(serial_port.name))
        raise BaseException("SerialPortInitFailed")


def pairing_uwb_ports(  oem_firmware=False, 
                        init_reporting=True, 
                        serial_ports_dict=None, 
                        stop_flag_callback=None):
    serial_tty_devices = [p.device for p in serial.tools.list_ports.comports() 
                            if p.manufacturer == 'SEGGER']
    try:
        serial_ports = {} if serial_ports_dict is None else serial_ports_dict
        opened_ports = []
        # Match the serial ports with the device list
        for dev in serial_tty_devices:
            try:
                p = serial.Serial(dev, baudrate=115200, timeout=3.0)
                opened_ports.append(p)
            except BaseException as e:
                raise e
            serial_port_available_check_flock(p)
            # Initialize the UART shell command
            if serial_port_uart_init(p):
                sys_info = parse_uart_sys_info(p, stop_flag_callback, verbose=True)
                if sys_info == -1: 
                    return -1
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
                    # TODO: Maybe later we can close the ports linking to the Slave/Anchors if no needs.
                    # TODO: (03272021) The needs to open slave/anchor ports are: determine local slaves or foreign slaves. 
                    # TODO: (03272021) Find a way around if slave serial ports cannot be opened (by discovery on 03272021).
                    # NOTE: (03282021) The way around: downgrade the slave fm to the OEM PANS firmware. Only keep the master's fw new.
                    # TODO: Add reverse compatibility to the rc.local if no display is connected.  
                    
                elif "tn" in sys_info["uwb_mode"]: 
                    serial_ports[uwb_addr_short]["config"] = "master"
                    master_info_dict = decode_info_pos_from_label(sys_info["label"])
                    master_info_dict["master_id"] = uwb_addr_short
                    serial_ports[uwb_addr_short]["info_pos"] = master_info_dict
                    
                    if init_reporting:
                        if oem_firmware:
                            if not is_reporting_loc(p):
                                # Type "lec\n" to the dwm shell console to activate data reporting
                                # TODO: try to determine if typing "lec\n" actually shuts off 
                                write_shell_command(p, command=b'\x6C\x65\x63\x0D', delay=0.2)
                        else:
                            # Write "aurs 1 1" to speed up data reporting into 0.1s/ea. (resume data reporting)
                            write_shell_command(p, command=b'\x61\x75\x72\x73\x20\x31\x20\x31\x0D', delay=0.2)
                else:
                    raise("unknown master/slave configuration!")

    except BaseException as e:
        return e
    return 1
    
    
def parse_uart_sys_info(serial_port, stop_flag_callback=None, verbose=False, attempt=5):
    """ Get the system config information of the tag device through UART

        :returns:
            Dictionary of system information
    """
    attempt_cnt = 1
    exception = None
    while attempt_cnt <= attempt:
        if stop_flag_callback is not None:
            if stop_flag_callback() == True:
                sys.stdout.write(timestamp_log() + "Stopped initializing UWB Ports\n")
                return -1
        try:
            if verbose:
                sys.stdout.write(timestamp_log() + "Fetching system information of UWB port {}, attempt: {}...\n".format(serial_port.name, attempt_cnt))
            sys_info = {}
            serial_port.reset_input_buffer()
            # make sure the shell command is entered.
            write_shell_command(serial_port, command=b'\x0D\x0D', delay=0.5)
            # Write "aurs 600 600" to slow down data reporting into 60s/ea.
            # "aurs 600 600\n"
            write_shell_command(serial_port, command=b'\x61\x75\x72\x73\x20\x36\x30\x30\x20\x36\x30\x30\x0D', delay=0.2 * (1 + attempt_cnt/10)) 
            # Write "si" to show system information of DWM1001
            write_shell_command(serial_port, command=b'\x73\x69\x0D', delay=0.2 * (1 + attempt_cnt/10))
            byte_si = serial_port.read(serial_port.in_waiting)
            si = str(byte_si, encoding="utf-8")
            if "aurs" not in si:
                sys.stdout.write(timestamp_log() + "Resetting reporting rate to 60s/ea. failed for port {}, preventing system info fetch. Retrying...\n".format(serial_port.name))
                # It is critical to reopen the UART comports. Otherwise the data won't go through. 
                serial_port.close()
                time.sleep(0.2)
                serial_port.open()
                continue
            if verbose:
                sys.stdout.write(timestamp_log() + "Raw system info of UWB port {} fetched as: \n".format(serial_port.name)
                                 + str(byte_si, encoding="utf-8") + "\n")
            
            # -------------- A selection of system information fields we need  --------------
            # -------------- Common, macro configurations  --------------
            # fw version
            sys_info["fw_ver"] = re.search("(?<=\sfw_ver=)(x[0-9a-fA-F]+)", si).group(0)
            # cfg version
            sys_info["cfg_ver"] = re.search("(?<=\scfg_ver=)(x[0-9a-fA-F]+)", si).group(0)
            # PANID in hexadecimal
            sys_info["panid"] = re.search("(?<=addr=)(x[0-9a-fA-F]+)", si).group(0)
            # Device ID in hexadecimal
            sys_info["addr"] = re.search("(?<=addr=)(.*?)(x[0-9a-fA-F]+)", si).group(0)
            # UWB mode
            sys_info["uwb_mode"] = re.search("(?<=\smode\:\s)(.*?)(?=\\r\\n)", si).group(0)
            # UWB mac status
            sys_info["uwbmac"] = re.search("(?<=\suwbmac\:\s)([a-z]+)(?=\s*.*uwbmac\:\sbh)", si).group(0)
            # UWB mac backhaul status
            sys_info["uwbmac_bh"] = re.search("(?<=\suwbmac\:\sbh\s)([a-z]+)(?=\s*)", si).group(0)
            
            # -------------- Common, micro configurations  --------------
            # fw update enabled, boolean
            sys_info["fwup"] = bool(int(re.search("(?<=\sfwup=)(.*)(?=\sble=)", si).group(0)))
            # BLE enabled, boolean
            sys_info["ble"] = bool(int(re.search("(?<=\sble=)(.*)(?=\sleds=)", si).group(0)))
            # Leds enabled, boolean
            sys_info["leds"] = bool(int(re.search("(?<=\sleds=)(.*)(?=\sinit=|\sle=)", si).group(0)))
            # Static update rate, int
            sys_info["upd_rate_stat"] = int(re.search("(?<=upd_rate_stat=)(.*)(?=\slabel)",si).group(0))
            # Label
            sys_info["label"] = re.search("(?<=label=)(.*?)(?=\\r\\n)",si).group(0)
            # Encryption enabled
            sys_info["enc"] = re.search("(?<=enc\:\s)(.*?)(?=\\r\\n)", si).group(0)
            # BLE address
            sys_info["ble_addr"] = re.search("(?<=\sble\:\saddr=)(.*?)(?=\\r\\n)",si).group(0)
            
            # -------------- Anchor speicfic  --------------
            if "an" in sys_info["uwb_mode"]:
                # Initiator, boolean
                sys_info["init"] = bool(int(re.search("(?<=\sinit=)(.*)(?=\supd_rate_stat=)", si).group(0)))

            # -------------- Tag speicfic  --------------
            if "tn" in sys_info["uwb_mode"]:
                # Location engine enabled, boolean
                sys_info["le"] = bool(int(re.search("(?<=\sle=)(.*)(?=\slp=)", si).group(0)))
                # Low power mode enabled, boolean
                sys_info["lp"] = bool(int(re.search("(?<=\slp=)(.*)(?=\sstat_det=)", si).group(0)))
                # Normal update rate, int
                sys_info["upd_rate_norm"] = int(re.search("(?<=upd_rate_norm=)(.*)(?=\supd_rate_stat=)",si).group(0))
            return sys_info
        
        except BaseException as e:
            attempt_cnt += 1
            exception = e

    sys.stdout.write(timestamp_log() + "Maximum attempt of {} to acquire system info of {} has reached. Failed. \n".format(attempt, serial_port.name))
    raise exception
        

def config_uart_settings(serial_port, settings):
    pass 


def make_json_dict_oem(raw_string):
    """ Parse the raw string reporting to make JSON-style dictionary
        sample input:
        les\n: 022E[7.94,8.03,0.00]=3.38 9280[7.95,0.00,0.00]=5.49 DCAE[0.00,8.03,0.00]=7.73 5431[0.00,0.00,0.00]=9.01 le_us=3082 est[6.97,5.17,-1.77,53]
        lep\n: POS,7.10,5.24,-2.03,53
        lec\n: DIST,4,AN0,022E,7.94,8.03,0.00,3.44,AN1,9280,7.95,0.00,0.00,5.68,AN2,DCAE,0.00,8.03,0.00,7.76,AN3,5431,0.00,0.00,0.00,8.73,POS,6.95,5.37,-1.97,52
        Notice: wrong-format (convoluted) UART reportings exist at high update rate. 
            e.g.(lec\n): 
            DIST,4,AN0,0090,0.00,0.00,0.00,3.25,AN1,D91E,0.00,0.00,0.00,3.33,AN2,0487,0.00,0.00,0.00,0.18,AN3,15BA,0.00,0,AN3,15BA,0.00,0.00,0.00,0.00
            AN3 is reported in a wrong format. Use regular expression to avoid discarding the entire reporting.
        :returns:
            Dictionary of parsed UWB reporting
    """
    try:
        data = {}
        # ---------parse for anchors and individual readings---------
        anc_match_iter = re.finditer(   "(?<=AN)(?P<anc_idx>[0-9]{1})[,]"
                                        "(?P<anc_id>.{4})[,]"
                                        "(?P<anc_x>[+-]?[0-9]*[.][0-9]{2})[,]"
                                        "(?P<anc_y>[+-]?[0-9]*[.][0-9]{2})[,]"
                                        "(?P<anc_z>[+-]?[0-9]*[.][0-9]{2})[,]"
                                        "(?P<dist_to>[+-]?[0-9]*[.][0-9]{2})", raw_string)
        all_anc_id = []
        num_anc = 0
        for regex_match in anc_match_iter:
            anc_id = regex_match.group("anc_id")
            all_anc_id.append(anc_id)
            data[anc_id] = {}
            data[anc_id]['anc_id'] = anc_id
            data[anc_id]['x'] = float(regex_match.group("anc_x"))
            data[anc_id]['y'] = float(regex_match.group("anc_y"))
            data[anc_id]['z'] = float(regex_match.group("anc_z"))
            data[anc_id]['dist_to'] = float(regex_match.group("dist_to"))
            num_anc += 1
        data['anc_num'] = num_anc
        data['all_anc_id'] = all_anc_id
        # ---------if location is calculated, parse calculated location---------
        pos_match = re.search("(?<=POS[,])"
                                "(?P<pos_x>[-+]?[0-9]*[.][0-9]{2})[,]"
                                "(?P<pos_y>[-+]?[0-9]*[.][0-9]{2})[,]"
                                "(?P<pos_z>[-+]?[0-9]*[.][0-9]{2})[,]"
                                "(?P<pos_qf>[0-9]*)", raw_string)
        if pos_match:
            data['est_pos'] = {}
            data['est_pos']['x'] = float(pos_match.group("pos_x"))
            data['est_pos']['y'] = float(pos_match.group("pos_y"))
            data['est_pos']['z'] = float(pos_match.group("pos_z"))
            data['est_pos_qf'] = int(pos_match.group("pos_qf"))
    except BaseException as e:
        sys.stdout.write(timestamp_log() + "JSON dictionary regex parsing failed: raw string: {} \n".format(raw_string))
        raise e
    return data


def make_json_dict_accel_en(raw_string):
    """ Parse the raw string reporting to make JSON-style dictionary, with the dwm-accelerometer-enabled firmware (unit in mm, all integers)
        sample input:
        DIST,4;[AN0,C584,160,0,-1510]=[1176,100];[AN1,8287,-2700,0,1340]=[2801,100];[AN2,DA36,400,3250,790]=[2838,100];[AN3,9234,2910,-2984,550]=[3058,100];POS=[502,827,803,58];ACC=[-512,768,9449];UWBLOCALTIME,38439537;
        Notice: wrong-format (convoluted) UART reportings may also exist at high update rate. Use regular expression to avoid discarding the entire reporting.
        :returns:
            Dictionary of parsed UWB reporting
    """
    try:
        data = {}
        # ---------parse for anchors and individual readings---------
        anc_match_iter = re.finditer(   "(?<=\[AN)(?P<anc_idx>[0-9]{1})[,]"
                                        "(?P<anc_id>.{4})[,]"
                                        "(?P<anc_x>[+-]?[0-9]*)[,]"
                                        "(?P<anc_y>[+-]?[0-9]*)[,]"
                                        "(?P<anc_z>[+-]?[0-9]*)(\]\=\[)"
                                        "(?P<dist_to>[+-]?[0-9]*)[,]"
                                        "(?P<anc_qf>[+-]?[0-9]*)(\]\;)", raw_string)
        all_anc_id = []
        num_anc = 0
        for regex_match in anc_match_iter:
            anc_id = regex_match.group("anc_id")
            all_anc_id.append(anc_id)
            data[anc_id] = {}
            data[anc_id]['anc_id'] = anc_id
            data[anc_id]['x'] = int(regex_match.group("anc_x"))
            data[anc_id]['y'] = int(regex_match.group("anc_y"))
            data[anc_id]['z'] = int(regex_match.group("anc_z"))
            data[anc_id]['dist_to'] = int(regex_match.group("dist_to"))
            data[anc_id]['anc_qf'] = int(regex_match.group("anc_qf"))
            num_anc += 1
        data['anc_num'] = num_anc
        data['all_anc_id'] = all_anc_id
        # ---------if location is calculated, parse calculated location---------
        pos_match = re.search("(?<=POS=\[)"
                              "(?P<pos_x>[-+]?[0-9]*)[,]"
                              "(?P<pos_y>[-+]?[0-9]*)[,]"
                              "(?P<pos_z>[-+]?[0-9]*)[,]"
                              "(?P<pos_qf>[-+]?[0-9]*)(\]\;)", raw_string)
        if pos_match:
            data['est_pos'] = {}
            data['est_pos']['x'] = int(pos_match.group("pos_x"))
            data['est_pos']['y'] = int(pos_match.group("pos_y"))
            data['est_pos']['z'] = int(pos_match.group("pos_z"))
            data['est_pos_qf'] = int(pos_match.group("pos_qf"))
            
        acc_match = re.search("(?<=ACC=\[)"
                              "(?P<acc_x>[-+]?[0-9]*)[,]"
                              "(?P<acc_y>[-+]?[0-9]*)[,]"
                              "(?P<acc_z>[-+]?[0-9]*)(\]\;)", raw_string)
        if acc_match:
            data['acc'] = {}
            data['acc']['x'] = int(acc_match.group("acc_x"))
            data['acc']['y'] = int(acc_match.group("acc_y"))
            data['acc']['z'] = int(acc_match.group("acc_z"))
        
        timestamp_match = re.search("(?<=UWBLOCALTIME)[,](?P<timestamp>[-+]?[0-9]*)[;]", raw_string)
        if timestamp_match:
            data['timestamp'] = int(timestamp_match.group("timestamp"))
            
    except BaseException as e:
        sys.stdout.write(timestamp_log() + "JSON dictionary regex parsing failed: raw string: {} \n".format(raw_string))
        raise e
    return data


def process_async_raw_ranging_results(  a_data_point, 
                                        b_data_point, 
                                        master_info_dict_a, 
                                        master_info_dict_b):
    # slaves on the same vehicle of the master has been already filtered-out. Sorted by UWB ranging distances.
    # Check time stamps first. 
    # if the same vehicle slaves were detected (2 slaves), input argument ranging_results_foreign_slaves_same_side could contain
    # at most 2 slaves. (max 4 slaves could be detected due to firmware restrictions.)
    slave_res_by_vehicles_a_side = defaultdict(list)
    slave_res_by_vehicles_b_side = defaultdict(list)
    [uwb_reporting_dict_a, ranging_results_foreign_slaves_from_a_master] = a_data_point
    [uwb_reporting_dict_b, ranging_results_foreign_slaves_from_b_master] = b_data_point
    # parse the slaves in distance-increasing order, for a side
    for ranging_dict in ranging_results_foreign_slaves_from_a_master:
        assoc_id = ranging_dict["id_assoc"]
        slave_res_by_vehicles_a_side[assoc_id].append(ranging_dict)
    # parse the slaves in distance-increasing order, for b side
    for ranging_dict in ranging_results_foreign_slaves_from_b_master:
        assoc_id = ranging_dict["id_assoc"]
        slave_res_by_vehicles_b_side[assoc_id].append(ranging_dict)
    ret_a, ret_b = [], []
    for (veh, slave_dicts) in slave_res_by_vehicles_a_side.items():
        # ----------- A end ranging results -----------
        vehicle_dict = {}
        vehicle_dict["vehicle_id"] = veh
        vehicle_dict["master_doing_ranging"] = master_info_dict_a
        vehicle_dict["slaves_in_ranging"] = slave_dicts
        vehicle_dict["near_side_code_local"] = determine_near_side_local(   veh,
                                                                            ranging_results_foreign_slaves_from_a_master,
                                                                            ranging_results_foreign_slaves_from_b_master,
                                                                            master_info_dict_a,
                                                                            master_info_dict_b,
                                                                            allow_unknown=False)
        vehicle_dict["near_side_code_foreign"] = determine_near_side_foreign(veh,
                                                                             ranging_results_foreign_slaves_from_a_master,
                                                                             ranging_results_foreign_slaves_from_b_master,
                                                                             master_info_dict_a,
                                                                             master_info_dict_b,
                                                                             allow_unknown=False)
        adjusted_dist = float('inf')
        if vehicle_dict["near_side_code_local"] == 2: # close side of foreign vehicle is B (self.A v.s. others.B)
            for ranging_res_dict in slave_dicts: 
                if ranging_res_dict["side_slave"] == 1: # self.A v.s. others.B.A_slave
                    if ranging_res_dict["id_assoc"] != vehicle_dict["vehicle_id"]:
                        continue
                    x_diff =   master_info_dict_a["x_master"] - ranging_res_dict['x_slave']
                    y_diff =   master_info_dict_a["y_master"] - ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_a["z_master"] - ranging_res_dict['z_slave']
                    try:
                        side_to_side_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        side_to_side_dist = float("nan")
                    adjusted_dist = min(side_to_side_dist, adjusted_dist)
                elif ranging_res_dict["side_slave"] == 2: # self.A v.s. others.B.B_slave
                    if ranging_res_dict["id_assoc"] != vehicle_dict["vehicle_id"]:
                        continue
                    x_diff =   master_info_dict_a["x_master"] + ranging_res_dict['x_slave']
                    y_diff =   master_info_dict_a["y_master"] + ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_a["z_master"] - ranging_res_dict['z_slave']
                    try:
                        side_to_side_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        side_to_side_dist = float("nan")
                    adjusted_dist = min(side_to_side_dist, adjusted_dist)
                else:
                    raise BaseException("A side: Undetermined side of the foreign vehicle slave unit.")
                ranging_res_dict["adjusted_dist"] = adjusted_dist
        elif vehicle_dict["near_side_code_local"] == 1: # close side of foreign vehicle is A (self.A v.s. others.A)
            for ranging_res_dict in slave_dicts: 
                if ranging_res_dict["side_slave"] == 2: # self.A v.s. others.A.B_slave
                    if ranging_res_dict["id_assoc"] != vehicle_dict["vehicle_id"]:
                        continue
                    x_diff =   master_info_dict_a["x_master"] - ranging_res_dict['x_slave']
                    y_diff =   master_info_dict_a["y_master"] - ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_a["z_master"] - ranging_res_dict['z_slave']
                    try:
                        side_to_side_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        side_to_side_dist = float("nan")
                    adjusted_dist = min(side_to_side_dist, adjusted_dist)
                elif ranging_res_dict["side_slave"] == 1: # self.A v.s. others.A.A_slave
                    if ranging_res_dict["id_assoc"] != vehicle_dict["vehicle_id"]:
                        continue
                    x_diff =   master_info_dict_a["x_master"] + ranging_res_dict['x_slave']
                    y_diff =   master_info_dict_a["y_master"] + ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_a["z_master"] - ranging_res_dict['z_slave']
                    try:
                        side_to_side_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        side_to_side_dist = float("nan")
                    adjusted_dist = min(side_to_side_dist, adjusted_dist)
                else:
                    raise BaseException("A side: Undetermined side of the foreign vehicle slave unit.")
                ranging_res_dict["adjusted_dist"] = adjusted_dist
        ret_a.append(vehicle_dict)

    for (veh, slave_dicts) in slave_res_by_vehicles_b_side.items():
        vehicle_dict = {}
        vehicle_dict["vehicle_id"] = veh
        vehicle_dict["master_doing_ranging"] = master_info_dict_b
        vehicle_dict["slaves_in_ranging"] = slave_dicts
        vehicle_dict["near_side_code_local"] = determine_near_side_local(   veh,
                                                                            ranging_results_foreign_slaves_from_b_master,
                                                                            ranging_results_foreign_slaves_from_a_master,
                                                                            master_info_dict_b,
                                                                            master_info_dict_a,
                                                                            allow_unknown=False)
        vehicle_dict["near_side_code_foreign"] = determine_near_side_foreign(veh,
                                                                             ranging_results_foreign_slaves_from_b_master,
                                                                             ranging_results_foreign_slaves_from_a_master,
                                                                             master_info_dict_b,
                                                                             master_info_dict_a,
                                                                             allow_unknown=False)
        adjusted_dist = float('inf')
        if vehicle_dict["near_side_code_local"] == 1: # close side of foreign vehicle is A (self.B v.s. others.A)
            for ranging_res_dict in slave_dicts: 
                if ranging_res_dict["side_slave"] == 1: # self.B v.s. others.A.A_slave
                    if ranging_res_dict["id_assoc"] != vehicle_dict["vehicle_id"]:
                        continue
                    x_diff =   master_info_dict_b["x_master"] + ranging_res_dict['x_slave']
                    y_diff =   master_info_dict_b["y_master"] + ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_b["z_master"] - ranging_res_dict['z_slave']
                    try:
                        side_to_side_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        side_to_side_dist = float("nan")
                    adjusted_dist = min(side_to_side_dist, adjusted_dist)
                elif ranging_res_dict["side_slave"] == 2: # self.B v.s. others.A.B_slave
                    if ranging_res_dict["id_assoc"] != vehicle_dict["vehicle_id"]:
                        continue
                    x_diff =   master_info_dict_b["x_master"] - ranging_res_dict['x_slave']
                    y_diff =   master_info_dict_b["y_master"] - ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_b["z_master"] - ranging_res_dict['z_slave']
                    try:
                        side_to_side_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        side_to_side_dist = float("nan")
                    adjusted_dist = min(side_to_side_dist, adjusted_dist)
                else:
                    raise BaseException("B side: Undetermined side of the foreign vehicle slave unit.")
                ranging_res_dict["adjusted_dist"] = adjusted_dist
        elif vehicle_dict["near_side_code_local"] == 2: # close side of foreign vehicle is B (self.B v.s. others.B)
            for ranging_res_dict in slave_dicts: 
                if ranging_res_dict["side_slave"] == 2: # self.B v.s. others.B.B_slave
                    if ranging_res_dict["id_assoc"] != vehicle_dict["vehicle_id"]:
                        continue
                    x_diff =   master_info_dict_b["x_master"] - ranging_res_dict['x_slave']
                    y_diff =   master_info_dict_b["y_master"] - ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_b["z_master"] - ranging_res_dict['z_slave']
                    try:
                        side_to_side_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        side_to_side_dist = float("nan")
                    adjusted_dist = min(side_to_side_dist, adjusted_dist)
                elif ranging_res_dict["side_slave"] == 1: # self.B v.s. others.B.A_slave
                    if ranging_res_dict["id_assoc"] != vehicle_dict["vehicle_id"]:
                        continue
                    x_diff =   master_info_dict_b["x_master"] + ranging_res_dict['x_slave']
                    y_diff =   master_info_dict_b["y_master"] + ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_b["z_master"] - ranging_res_dict['z_slave']
                    try:
                        side_to_side_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        side_to_side_dist = float("nan")
                    adjusted_dist = min(side_to_side_dist, adjusted_dist)
                else:
                    raise BaseException("B side: Undetermined side of the foreign vehicle slave unit.")
                ranging_res_dict["adjusted_dist"] = adjusted_dist
        ret_b.append(vehicle_dict)
    return ret_a, ret_b


def process_sycned_raw_ranging_results( ranging_results_foreign_slaves_same_side,
                                        ranging_results_foreign_slaves_opposite_side,
                                        master_info_dict_same_side,
                                        master_info_dict_opposite_side):
    # slaves on the same vehicle of the master has been already filtered-out. Sorted by UWB ranging distances.
    # if the same vehicle slaves were detected (2 slaves), input argument ranging_results_foreign_slaves_same_side could contain
    # at most 2 slaves. (max 4 slaves could be detected due to firmware restrictions.)
    slave_res_by_vehicles = defaultdict(list)
    
    # parse the slaves in distance-increasing order
    for ranging_dict in ranging_results_foreign_slaves_same_side:
        assoc_id = ranging_dict["id_assoc"]
        slave_res_by_vehicles[assoc_id].append(ranging_dict)
    ret = []
    for (veh, slave_dicts) in slave_res_by_vehicles.items():
        vehicle_dict = {}
        vehicle_dict["vehicle_id"] = veh
        vehicle_dict["master_doing_ranging"] = master_info_dict_same_side
        vehicle_dict["near_side_code_foreign"] = determine_near_side_foreign(veh,
                                                                             ranging_results_foreign_slaves_same_side,
                                                                             ranging_results_foreign_slaves_opposite_side,
                                                                             master_info_dict_same_side,
                                                                             master_info_dict_opposite_side,
                                                                             allow_unknown=False)
        vehicle_dict["near_side_code_local"] = determine_near_side_local(veh,
                                                                         ranging_results_foreign_slaves_same_side,
                                                                         ranging_results_foreign_slaves_opposite_side,
                                                                         master_info_dict_same_side,
                                                                         master_info_dict_opposite_side,
                                                                         allow_unknown=False)
        vehicle_dict["slaves_in_ranging"] = slave_dicts
        if master_info_dict_same_side["side_master"] != vehicle_dict["near_side_code_local"]:
            # if the current master is not on the side near the current vehicle.
            # TODO: this value may still be useful for other use cases. e.g. determination of relative
            # positions when multiple tracks are involved (2-D dimensions).
            for ranging_res_dict in slave_dicts: 
                if ranging_res_dict["side_slave"] != vehicle_dict["near_side_code_foreign"]:
                    # process the far side of the foreign vehicle (non-safety critical).
                    x_diff =   master_info_dict_same_side["x_master"] + ranging_res_dict['x_slave']
                    y_diff = - master_info_dict_same_side["y_master"] - ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_same_side["z_master"] - ranging_res_dict['z_slave']
                    try:
                        adjusted_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) + x_diff)
                    except:
                        adjusted_dist = float("nan")
                elif ranging_res_dict["side_slave"] == vehicle_dict["near_side_code_foreign"]:
                    # process the near side of the foreign vehicle (non safety critical).
                    x_diff =   master_info_dict_same_side["x_master"] - ranging_res_dict['x_slave']
                    y_diff = - master_info_dict_same_side["y_master"] + ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_same_side["z_master"] - ranging_res_dict['z_slave']
                    try:
                        adjusted_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) + x_diff)
                    except:
                        adjusted_dist = float("nan")
                else:
                    raise BaseException("Undetermined side of the foreign vehicle slave unit.")
                ranging_res_dict["adjusted_dist"] = adjusted_dist
        elif master_info_dict_same_side["side_master"] == vehicle_dict["near_side_code_local"]:
            # if the current master is exactly the side near the current vehicle.
            # TODO: this value may still be useful for other use cases. e.g. determination of relative
            # positions when multiple tracks are involved (2-D dimensions).
            for ranging_res_dict in slave_dicts: 
                if ranging_res_dict["side_slave"] != vehicle_dict["near_side_code_foreign"]:
                    # process the far side of the foreign vehicle (non-safety critical).
                    x_diff =   master_info_dict_same_side["x_master"] - ranging_res_dict['x_slave']
                    y_diff = - master_info_dict_same_side["y_master"] + ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_same_side["z_master"] - ranging_res_dict['z_slave']
                    try:
                        adjusted_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        adjusted_dist = float("nan")
                elif ranging_res_dict["side_slave"] == vehicle_dict["near_side_code_foreign"]:
                    # process the near side of the foreign vehicle (safety critical!).
                    x_diff =   master_info_dict_same_side["x_master"] + ranging_res_dict['x_slave']
                    y_diff = - master_info_dict_same_side["y_master"] - ranging_res_dict['y_slave']
                    z_diff =   master_info_dict_same_side["z_master"] - ranging_res_dict['z_slave']
                    try:
                        adjusted_dist = int(math.sqrt(ranging_res_dict["dist_to"]**2 - z_diff**2 - y_diff**2) - x_diff)
                    except:
                        adjusted_dist = float("nan")
                else:
                    raise BaseException("Undetermined side of the foreign vehicle slave unit.")
                ranging_res_dict["adjusted_dist"] = adjusted_dist
        else:
            raise BaseException("Undetermined side of the local vehicle master unit.")
        ret.append(vehicle_dict)
    return ret


def determine_near_side_foreign(vehicle,
                                same_side_ranging_slave_dicts,
                                oppo_side_ranging_slave_dicts,
                                same_side_master_dict,
                                oppo_side_master_dict,
                                allow_unknown=False):
    # This is a naive method to temporarily determine the side of the slave of the foreign vehicle
    # TODO: fine-tune the determination algorithm to cover the corner cases, especially the 2-D cases (not the same track)
    side_code, dist_to = 0, float("inf")
    for ranging_dict in same_side_ranging_slave_dicts:
        if ranging_dict["id_assoc"] == vehicle:
            if ranging_dict["dist_to"] < dist_to:
                dist_to = ranging_dict["dist_to"]
                side_code = ranging_dict["side_slave"]
            
    if allow_unknown:
        return side_code
    elif side_code != 0:
        return side_code
    else:
        raise BaseException("Unable to determine near side of the foreign vehicle, association id: {}".format(vehicle))


def determine_near_side_local(vehicle,
                              same_side_ranging_slave_dicts,
                              oppo_side_ranging_slave_dicts,
                              same_side_master_dict,
                              oppo_side_master_dict,
                              allow_unknown=False):
    # This is a naive method to temporarily determine the side of the master that is closest to the foreign vehicle
    # TODO: fine-tune the determination algorithm to cover the corner cases, especially the 2-D cases (not the same track)
    side_code, dist_to = 0, float("inf")
    for ranging_dict in same_side_ranging_slave_dicts:
        if ranging_dict["dist_to"] < dist_to:
            dist_to = ranging_dict["dist_to"]
            side_code = same_side_master_dict["side_master"]
    for ranging_dict in oppo_side_ranging_slave_dicts:
        if ranging_dict["dist_to"] < dist_to:
            dist_to = ranging_dict["dist_to"]
            side_code = oppo_side_master_dict["side_master"]
        
    if allow_unknown:
        return side_code
    elif side_code != 0:
        return side_code
    else:
        raise BaseException("Unable to determine near side of the foreign vehicle, association id: {}".format(vehicle))


def decode_info_pos_from_label(label_string):
    info_pos_bytes = base64.b64decode(label_string)
    ret = {}
    ret["x_master"] = int.from_bytes(bytearray([info_pos_bytes[0], info_pos_bytes[1]]), 'little', signed=True) * 10
    ret["y_master"] = int.from_bytes(bytearray([info_pos_bytes[2], info_pos_bytes[3]]), 'little', signed=True) * 10
    ret["z_master"] = int.from_bytes(bytearray([info_pos_bytes[4], info_pos_bytes[5]]), 'little', signed=False) * 10
    ret["vehicle_length_master"] = int.from_bytes(bytearray([info_pos_bytes[8], info_pos_bytes[9]]), 'little', signed=False) * 10
    ret["id_assoc"] = int.from_bytes(bytearray([info_pos_bytes[6]]), 'little', signed=False)
    side_int = int.from_bytes(bytearray([info_pos_bytes[7]]), 'little', signed=False)
    ret["side_master"] = side_int
    # side_int 1: "B"; 2: "A"; 0: "UNKNOWN"
    return ret


def decode_slave_info_position(ranging_json_dict):
    # decode the slave informative position from ranging dictionary, generated by 
    # make_json_dict_accel_en().
    # Note: only results generated with make_json_dict_accel_en() with matching UWB
    # firmware will yield the expected results. Acceleration values will be compromised otherwise.
    # End side information is encoded with a Modulo-3 method in the integer of Z field (TOR). Z (TOR) field is unsigned.
    slave_info_dict = {}
    slave_info_dict["all_anc_id"] = ranging_json_dict.get("all_anc_id", [])
    for anc in ranging_json_dict.get("all_anc_id", []):
        slave_reporting_raw = ranging_json_dict.get(anc, {})
        slave_x_regular_pos = slave_reporting_raw.get('x', int(0))
        slave_y_regular_pos = slave_reporting_raw.get('y', int(0))
        slave_z_regular_pos = slave_reporting_raw.get('z', int(0))
        slave_qf_regular_pos = slave_reporting_raw.get('anc_qf', int(0))
        slave_dist_to = slave_reporting_raw.get('dist_to', int(0))
        recover_bytes = bytearray()
        recover_bytes.extend(slave_x_regular_pos.to_bytes(4, "little", signed=True))
        recover_bytes.extend(slave_y_regular_pos.to_bytes(4, "little", signed=True))
        recover_bytes.extend(slave_z_regular_pos.to_bytes(4, "little", signed=True))
        recover_bytes.extend(slave_qf_regular_pos.to_bytes(1, "little", signed=False))
        x_slave = int.from_bytes(bytearray([recover_bytes[2], recover_bytes[3]]), 'little', signed=True)
        y_slave = int.from_bytes(bytearray([recover_bytes[6], recover_bytes[7]]), 'little', signed=True)
        z_slave = int.from_bytes(bytearray([recover_bytes[10], recover_bytes[11]]), 'little', signed=False)
        vehicle_length_slave = int.from_bytes(bytearray([recover_bytes[8], recover_bytes[9]]), 'little', signed=False)
        id_slave = int.from_bytes(bytearray([recover_bytes[1]]), 'little', signed=False)
        side_slave = z_slave % 3
        slave_info_dict[anc] = {}
        slave_info_dict[anc]['slave_id'] = anc
        slave_info_dict[anc]['x_slave'] = x_slave * 10
        slave_info_dict[anc]['y_slave'] = y_slave * 10
        slave_info_dict[anc]['z_slave'] = z_slave * 10
        slave_info_dict[anc]['vehicle_length_slave'] = vehicle_length_slave * 10
        slave_info_dict[anc]['id_assoc'] = id_slave
        slave_info_dict[anc]['side_slave'] = side_slave
        slave_info_dict[anc]['dist_to'] = slave_reporting_raw.get('dist_to', int(0))
    return slave_info_dict


def side_name_from_code(side_code):
    if side_code == 2:
        return "A"
    elif side_code == 1:
        return "B"
    else:
        return "UNKNOWN"


def parse_distance(dist_in_mm, length_unit):
    if length_unit in ("METRIC", "metric", "mm"):
        return str(dist_in_mm) + " mm"
    elif length_unit in ("IMPERIAL", "imperial", "in"):
        return str(round(dist_in_mm * 0.0393701, 1)) + " \""
    else:
        return "UNKNOWN"


def display_safety_ranging_results(processed_master_reporting_by_vehicles, length_unit="METRIC", debug=False):
    # End Sample Reporting (processed and adjusted): 
    # [{'vehicle_id': 2, 'master_doing_ranging': {}, 'near_side_code_foreign': 2, 'near_side_code_local': 2, 'slaves_in_ranging': [{'slave_id': '0B1E', 'x_slave': 20, 'y_slave': -3190, 'z_slave': 740, 'vehicle_length_slave': 930, 'id_assoc': 2, 'side_slave': 2, 'dist_to': 3658, 'adjusted_dist': 1763}, {'slave_id': '459A', 'x_slave': 30, 'y_slave': 3370, 'z_slave': 790, 'vehicle_length_slave': 930, 'id_assoc': 2, 'side_slave': 1, 'dist_to': 4520, 'adjusted_dist': 3040}]}]
    # TODO: convert the raw data into either JSON format or CSV format
    if debug:
        return repr(processed_master_reporting_by_vehicles), -1
    if not processed_master_reporting_by_vehicles:
        return "UWB Detection Results N/A Yet", -1
    for veh_dict in processed_master_reporting_by_vehicles:
        vehicle_id, master_side_code = veh_dict["vehicle_id"], veh_dict["master_doing_ranging"]["side_master"]
        
        if master_side_code != veh_dict["near_side_code_local"]:
            return "{} side: No Vehicle Detected".format(side_name_from_code(master_side_code)), -2
        elif veh_dict["master_doing_ranging"]["side_master"] == veh_dict["near_side_code_local"]:
            vehicle_adjusted_dist_mm = [slave_dict["adjusted_dist"] for slave_dict in veh_dict["slaves_in_ranging"] 
                                            if slave_dict["side_slave"] == veh_dict["near_side_code_foreign"]]
            if len(vehicle_adjusted_dist_mm) > 0:
                return "{} side: Detected Vehicle {}: {}".format(   side_name_from_code(master_side_code),
                                                                    vehicle_id,
                                                                    parse_distance(vehicle_adjusted_dist_mm[0], length_unit)), vehicle_adjusted_dist_mm[0]
            else:
                return "{} side: No Vehicle Detected! ".format(side_name_from_code(master_side_code)), -2
        else:
            return "{} side: Detection Results N/A. Error".format(side_name_from_code(master_side_code)), -3


def end_ranging_job_async_single(   serial_ports,
                                    end_side_code,
                                    data_ptr_queue_single_end,
                                    log_fpath,
                                    stop_flag_callback=None,
                                    oem_firmware=False,
                                    exp_name=""):
    while not serial_ports:
        time.sleep(0.1)
        continue

    master_dev_id = ""
    master_info_pos = {}
    while master_dev_id == "":
        if stop_flag_callback is not None:
            if stop_flag_callback() == True:
                return
        serial_ports_local_copy = serial_ports.copy()
        for dev in serial_ports_local_copy:
            if serial_ports_local_copy[dev]["info_pos"].get("side_master") == end_side_code:
                master_dev_id = dev
                master_info_pos = serial_ports_local_copy[dev]["info_pos"]
                break

    data_pointer = [{}, []]
    port_master = serial_ports[master_dev_id].get("port")
    try:
        if not port_master.is_open:
            port_master.open()
    except serial.serialutil.SerialException as e:
        raise e
    if not is_reporting_loc(port_master):
        if oem_firmware:
            # Type "lec\n" to the dwm shell console to activate data reporting
            write_shell_command(port_master, command=b'\x6C\x65\x63\x0D', delay=0.2) 
        else:
            # Write "aurs 1 1" to speed up data reporting into 0.1s/ea.
            write_shell_command(port_master, command=b'\x61\x75\x72\x73\x20\x31\x20\x31\x0D', delay=0.2)

    super_frame = 0
    end_name = "A" if end_side_code == 2 else "B" if end_side_code == 1 else "UNKNOWN"
    try:
        port_master.reset_input_buffer()
    except serial.serialutil.SerialException as e:
        print(port_master, serial_ports)
        raise e
    sys.stdout.write(timestamp_log() + end_name + " end reporting thread started. See processed data entries in file: {}\n".format("data-"+end_name+"-uwb-"+exp_name+"_log.log"))
    sys.stdout.write(timestamp_log() + end_name + " end reporting thread started. See raw data entries in file: {}\n".format("data-"+end_name+"-raw-"+exp_name+"_log.log"))

    while True:
        if stop_flag_callback is not None:
            if stop_flag_callback() == True:
                sys.stdout.write(timestamp_log() + end_name + " end reporting thread stopped. See data entries in file: {}\n".format("data-"+end_name+"-uwb-"+exp_name+"_log.log"))
                sys.stdout.write(timestamp_log() + end_name + " end reporting thread stopped. See raw data entries in file: {}\n".format("data-"+end_name+"-raw-"+exp_name+"_log.log"))
                return
        try:
            data_raw = str(port_master.readline(), encoding="UTF-8").rstrip()
            timestamp = timestamp_log()
            if not data_raw[:4] == "DIST":
                continue
            if oem_firmware:
                uwb_reporting_dict = make_json_dict_oem(data_raw)
            else:
                uwb_reporting_dict = make_json_dict_accel_en(data_raw)
            slave_reporting_dict = decode_slave_info_position(uwb_reporting_dict)
            uwb_reporting_dict['superFrameNumber'] = super_frame
            uwb_reporting_dict['timeStamp'] = timestamp
            uwb_reporting_dict['masterInfoPos'] = master_info_pos
            ranging_results_foreign_slaves_from_master = []
            for anc in uwb_reporting_dict.get("all_anc_id", []):
                if not serial_ports.get(anc):
                    # If the anchor/slave id is not recognized, it is from foreign vehicle (filter out local slaves). 
                    ranging_results_foreign_slaves_from_master.append(slave_reporting_dict.get(anc, {}))
            # Sort by proximity - nearest slave first
            ranging_results_foreign_slaves_from_master.sort(key=lambda x: x.get("dist_to", float("inf")))
            data_pointer[0] = uwb_reporting_dict
            # We DO NOT process the raw ranging slave results. Instead, we report them async, incl. timestamp
            # and have the external process/thread to process the slave results (because being async)
            data_pointer[1] = ranging_results_foreign_slaves_from_master
            super_frame += 1
            data_ptr_queue_single_end.put(data_pointer)

            # wait for new UWB reporting results
            with open(os.path.join(log_fpath, "data-"+end_name+"-uwb-"+exp_name+"_log.log"), "a") as d_log:
                d_log.write(timestamp + end_name + " end reporting uwb data: " + repr(data_pointer[0]) + "\n")
                d_log.write(timestamp + end_name + " end reporting decoded foreign slaves: " + repr(data_pointer[1]) + "\n")
            
            with open(os.path.join(log_fpath, "data-"+end_name+"-raw-"+exp_name+"_log.log"), "a") as raw_log:
                raw_log.write(timestamp + end_name + " end reporting raw data: " + data_raw + "\n")
            
        except Exception as exp:
            timestamp = timestamp_log()
            data_raw = str(port_master.readline(), encoding="UTF-8").rstrip()
            sys.stdout.write(timestamp + end_name + " end reporting thread failed. Last fetched UART data: {}. Thread: {}\n"
                             .format(data_raw, threading.current_thread().getName()))
            raise exp


if __name__ == "__main__":
    # Unit Testing
    unittest = decode_slave_info_position
    unittest_input_0 = "DIST,4,AN0,0090,0.00,0.00,0.00,-3.25,AN1,D91E,0.00,0.00,0.00,3.33,AN2,0487,0.00,0.00,0.00,0.18,AN3,15BA,0.00,0,AN3,15BA,0.00,0.00,0.00,0.00"
    unittest_input_1 = "DIST,4,AN0,0090,0.00,0.00,0.00,-3.25,AN1,D91E,-0.00,0.00,0.00,3.33,AN2,0487,0.00,0.00,0.00,0.18,AN3,15BA,0.00,0,AN3,15BA,0.00,0.00,0.00,0.00,POS,6.95,5.37,-1.97,52"
    input_1 = {'all_anc_id':['459A','0B1E'],'459A':{'anc_id': '459A', 'x': -1525078912, 'y': -60523264, 'z': 63744, 'dist_to': 2833, 'anc_qf': 100}, '0B1E':{'anc_id': '0B1E', 'x': -870767360, 'y': -60522752, 'z': 64256, 'dist_to': 2969, 'anc_qf': 100}}
    
    print(unittest(input_1))
    
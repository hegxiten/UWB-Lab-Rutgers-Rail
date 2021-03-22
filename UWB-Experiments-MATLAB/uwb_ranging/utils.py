from datetime import datetime
import sys, time, json, re, base64, math
import atexit, signal


def load_config_json(json_path):
    raise("loading json is deprecated! ")
    try:
        with open(json_path) as f:
            config_dict = json.load(f)
            for dev in config_dict["uwb_devices"]:
                if config_dict[dev]["config"] == "master":
                    if config_dict[dev]["end_side"] == "a":
                        config_dict["a_end_master"] = dev
                    if config_dict[dev]["end_side"] == "b":
                        config_dict["b_end_master"] = dev
                if config_dict[dev]["config"] == "slave":
                    if config_dict[dev]["end_side"] == "a":
                        config_dict["a_end_slave"] = dev
                    if config_dict[dev]["end_side"] == "b":
                        config_dict["b_end_slave"] = dev
            return config_dict
    except BaseException as e:
        sys.stdout.write(timestamp_log() + "failed to load JSON configuration file\n")
        raise e


def timestamp_log(incl_UTC=False):
    """ Get the timestamp for the stdout log message
        
        :returns:
            string format local timestamp with option to include UTC 
    """
    local_timestp = "["+str(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))+" local] "
    utc_timestp = "["+str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))+" UTC] "
    if incl_UTC:
        return local_timestp + utc_timestp
    else:
        return local_timestp


def write_shell_command(serial_port, command, delay=0.1):
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
    if sys.platform.startswith('linux'):
        import fcntl
        fcntl.flock(serial_port, fcntl.LOCK_UN)
    serial_port.close()


def on_killed(serial_port, signum, frame):
    """ Closure function as handler to signal.signal in order to pass serial port name
    """
    # if killed by UNIX, no need to execute on_exit callback
    atexit.unregister(on_exit)
    sys.stdout.write(timestamp_log() + "Serial port {} closed on killed\n".format(serial_port.name))
    if sys.platform.startswith('linux'):
        import fcntl
        fcntl.flock(serial_port, fcntl.LOCK_UN)
    serial_port.close()


def port_available_check(serial_port):
    if sys.platform.startswith('linux'):
        import fcntl
    try:
        fcntl.flock(serial_port, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, BlockingIOError) as exp:
        sys.stdout.write(timestamp_log() + "Serial port {} is busy. Another process is accessing the port. \n".format(serial_port.name))
        raise exp
    else:
        sys.stdout.write(timestamp_log() + "Serial port {} is ready.\n".format(serial_port.name))


def parse_uart_init(serial_port):
    raise BaseException("Function Must Be Overriden!")


def is_uwb_shell_ok(serial_port, verbose=False):
    """ Detect if the DWM1001 Tag's shell console is responding to \x0D\x0D
        
        :returns:
            True or False
    """
    serial_port.reset_input_buffer()
    write_shell_command(serial_port, command=b'\x0D\x0D')
    if serial_port.in_waiting:
        return True
    return False


def is_reporting_loc(serial_port, timeout=1, verbose=False):
    """ Detect if the DWM1001 Tag is running on data reporting mode
        
        :returns:
            True or False
    """
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

    
def parse_uart_sys_info(serial_port, oem_firmware=False, verbose=False, attempt=5):
    """ Get the system config information of the tag device through UART

        :returns:
            Dictionary of system information
    """
    attempt_cnt = 1
    exception = None
    while attempt_cnt <= attempt:
        try:
            if verbose:
                sys.stdout.write(timestamp_log() + "Fetching system information of UWB port {}, attempt: {}...\n".format(serial_port.name, attempt_cnt))
            sys_info = {}
            if is_reporting_loc(serial_port):
                if oem_firmware:
                    # Write "lec" to stop data reporting
                    write_shell_command(serial_port, command=b'\x6C\x65\x63\x0D', delay=0.5)
                else:
                    # Write "aurs 600 600" to slow down data reporting into 60s/ea.
                    write_shell_command(serial_port, command=b'\x61\x75\x72\x73\x20\x36\x30\x30\x20\x36\x30\x30\x0D', delay=0.5) # "aurs 600 600\n"
                    
            # Write "si" to show system information of DWM1001
            serial_port.reset_input_buffer()
            write_shell_command(serial_port, command=b'\x73\x69\x0D', delay=0.5)
            byte_si = serial_port.read(serial_port.in_waiting)
            si = str(byte_si, encoding="utf-8")
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
            

def parse_info_position_from_label(label_string):
    info_pos_bytes = base64.b64decode(label_string)
    ret = {}
    ret["x_master"] = int.from_bytes(bytearray([info_pos_bytes[0], info_pos_bytes[1]]), 'little', signed=True) * 10
    ret["y_master"] = int.from_bytes(bytearray([info_pos_bytes[2], info_pos_bytes[3]]), 'little', signed=True) * 10
    ret["z_master"] = int.from_bytes(bytearray([info_pos_bytes[4], info_pos_bytes[5]]), 'little', signed=False) * 10
    ret["id_assoc"] = int.from_bytes(bytearray([info_pos_bytes[6]]), 'little', signed=False)
    side_int = int.from_bytes(bytearray([info_pos_bytes[7]]), 'little', signed=False)
    if side_int == 1:
        ret["side_master"] = "B"
    elif side_int == 2:
        ret["side_master"] = "A"
    else:
        ret["side_master"] = "UNKNOWN"
    return ret
        

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


def calculate_adjusted_dist(ranging_results_all_slaves, master_info_dict):
    ret = []
    for (anc, ranging_dict) in ranging_results_all_slaves:
        dist = ranging_dict["dist_to"]
        
        y_diff = abs(master_info_dict["y_master"] - (-ranging_dict['y_slave']))
        z_diff = abs(master_info_dict["z_master"] - ranging_dict['z_slave'])
        try:
            adjusted_dist = math.sqrt(dist**2 - z_diff**2 - y_diff**2) - master_info_dict["x_master"] - ranging_dict['x_slave']
            # TODO: determine the different scenarios of y_diff: side dependent. 
            ranging_dict["adjusted_dist"] = int(adjusted_dist)
        except:
            ranging_dict["adjusted_dist"] = -1
    return ranging_results_all_slaves
    

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
        id_slave = int.from_bytes(bytearray([recover_bytes[1]]), 'little', signed=False)
        side_slave = z_slave % 3
        slave_info_dict[anc] = {}
        slave_info_dict[anc]['x_slave'] = x_slave * 10
        slave_info_dict[anc]['y_slave'] = y_slave * 10
        slave_info_dict[anc]['z_slave'] = z_slave * 10
        slave_info_dict[anc]['id_assoc'] = id_slave
        slave_info_dict[anc]['side_slave'] = side_slave
        slave_info_dict[anc]['dist_to'] = slave_reporting_raw.get('dist_to', int(0))
    return slave_info_dict

if __name__ == "__main__":
    unittest = decode_slave_info_position
    unittest_input_0 = "DIST,4,AN0,0090,0.00,0.00,0.00,-3.25,AN1,D91E,0.00,0.00,0.00,3.33,AN2,0487,0.00,0.00,0.00,0.18,AN3,15BA,0.00,0,AN3,15BA,0.00,0.00,0.00,0.00"
    unittest_input_1 = "DIST,4,AN0,0090,0.00,0.00,0.00,-3.25,AN1,D91E,-0.00,0.00,0.00,3.33,AN2,0487,0.00,0.00,0.00,0.18,AN3,15BA,0.00,0,AN3,15BA,0.00,0.00,0.00,0.00,POS,6.95,5.37,-1.97,52"
    input_1 = {'all_anc_id':['459A','0B1E'],'459A':{'anc_id': '459A', 'x': -1525078912, 'y': -60523264, 'z': 63744, 'dist_to': 2833, 'anc_qf': 100}, '0B1E':{'anc_id': '0B1E', 'x': -870767360, 'y': -60522752, 'z': 64256, 'dist_to': 2969, 'anc_qf': 100}}
    
    print(unittest(input_1))
    
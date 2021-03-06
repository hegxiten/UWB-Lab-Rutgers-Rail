from datetime import datetime
from time import localtime
import os, sys, time, json, re
import atexit, signal


def load_config_json(json_path):
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
    lt = localtime()
    local_timestp = "["+str(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))[:-3]+ " "+ lt.tm_zone + "] "
    utc_timestp = "["+str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))[:-3]+" UTC] "
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


def get_tag_serial_port(verbose=False):
    """ Detect the serial port name of DWM1001 Tag

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            return DWM1001 tag serial port name and make sure it is closed
    """
    if verbose:
        sys.stdout.write(timestamp_log() + "Fetching serialport...\n")
    ports = []
    import serial.tools.list_ports
    if sys.platform.startswith('win'):
        # assume there is only one J-Link COM port
        # ports += [str(i).split(' - ')[0]
        #             for  i in serial.tools.list_ports.comports() 
        #             if "JLink" in str(i)]
        ports = ['COM5']
    elif sys.platform.startswith('linux'):
        # the UART between RPi adn DWM1001-Dev is designated as serial0
        # with the drivers installed. 
        # see Section 4.3.1.2 of DWM1001-Firmware-User-Guide
        if re.search("raspberrypi", str(os.uname())):
            ports += ["/dev/serial0"]
        else:
            ports += glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.usbmodem*')
    else:
        raise EnvironmentError('Unsupported platform')
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
        except BaseException as e:
            print("Wrong serial port detected for UWB tag")
            raise e
    if verbose:
        sys.stdout.write(timestamp_log() + "Serialport fetched as: " + str(ports))
    return ports


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


def available_ttys(portlist):
    """ Generator to yield all available ports that are not locked by flock.
        Filters out the ports that are already opened. Preventing the program
        from running on multilple processes.
        
        Notice: if the other processes don't use flock, that process(es) will
        still be able to open the port, skipping the flock protection.
        
        Only works for POSIX/LINUX environment. 
        
        :yield:timestamp_log() + "Port is busy\n"
            Comports that aren't locked by flock.
    """
    assert sys.platform.startswith('linux')
    for tty in portlist:
        try:
            port = serial.Serial(port=tty[0])
            if port.isOpen():
                try:
                    fcntl.flock(port.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (IOError, BlockingIOError):
                    sys.stdout.write(timestamp_log() + "Port is busy\n")
                else:
                    yield port
        except serial.SerialException as ex:
            print('Port {0} is unavailable: {1}'.format(tty, ex))


def parse_uart_init(serial_port):
    # register the callback functions when the service ends
    # atexit for regular exit, signal.signal for system kills    
    atexit.register(on_exit, serial_port, True)
    signal.signal(signal.SIGTERM, on_killed)
    # Pause for 0.1 sec after establishment
    time.sleep(0.1)
    # Double enter (carriage return) as specified by Decawave
    serial_port.write(b'\x0D\x0D')
    time.sleep(0.1)
    serial_port.reset_input_buffer()

    # By default the update rate is 10Hz/100ms. Check again for data flow
    # if data is flowing, stop the data flow (temporarily) to execute commands.
    if is_reporting_loc(serial_port):
        serial_port.write(b'\x6C\x65\x63\x0D')
        time.sleep(0.1)
    

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
    attempt_cnt = 0
    while attempt_cnt <= attempt:
        try:
            if verbose:
                sys.stdout.write(timestamp_log() + "Fetching system information of UWB port {}, attempt: {}...\n".format(serial_port.name, attempt_cnt))
            sys_info = {}
            if is_reporting_loc(serial_port):
                if oem_firmware:
                    # Write "lec" to stop data reporting
                    write_shell_command(serial_port, command=b'\x6C\x65\x63\x0D')
                else:
                    # Write "aurs 600 600" to slow down data reporting into 60s/ea.
                    write_shell_command(serial_port, command=b'\x61\x75\x72\x73\x20\x36\x30\x30\x20\x36\x30\x30\x0D') # "aurs 600 600\n"
                    
            # Write "si" to show system information of DWM1001
            serial_port.reset_input_buffer()
            write_shell_command(serial_port, command=b'\x73\x69\x0D')
            byte_si = serial_port.read(serial_port.in_waiting)
            si = str(byte_si)
            if verbose:
                sys.stdout.write(timestamp_log() + "Raw system info of UWB port {} fetched as: \n".format(serial_port.name)
                                 + str(byte_si, encoding="UTF-8") + "\n")
            # PANID in hexadecimal
            pan_id = re.search("(?<=uwb0\:\spanid=)(.{5})(?=\saddr=)", si).group(0)
            sys_info["pan_id"] = pan_id
            # Device ID in hexadecimal
            device_id = re.search("(?<=panid=.{6}addr=)(.{17})", si).group(0)
            sys_info["device_id"] = device_id
            # Update rate of location reporting in int
            upd_rate = re.search("(?<=upd_rate_stat=)(.*)(?=\slabel=)",si).group(0)
            sys_info["upd_rate"] = int(upd_rate)
            
            return sys_info
        except:
            attempt_cnt += 1
    sys.stdout.write(timestamp_log() + "Maximum attempt of {} to acquire system info of {} has reached. Failed. \n".format(attempt, serial_port.name))
    raise BaseException("UWB Shell Command Error")


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


if __name__ == "__main__":
    unittest = timestamp_log

    print(unittest())
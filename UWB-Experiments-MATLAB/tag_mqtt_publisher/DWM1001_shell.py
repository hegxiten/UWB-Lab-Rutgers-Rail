import time, serial
from datetime import datetime
import sys

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


def dwm_cfg_tag_set_shell_acts(serial_port, 
                        loc_en, max_retrials, retrial_cnt=0, 
                        meas_mode=0, stnry_en=1, low_pwr=0, enc=0, leds=1, ble=1, uwb=2, fw_upd=0, reset=False):
    """ Use shell command 'acts' as provided shell api to configure tag 
        usage:
        acts <meas_mode> <stnry_en> <low_pwr> <loc_en> <enc> <leds> <ble> <uwb> <fw_upd>
        
        :returns:
            True or False
    """
    
    shell_cmd = 'acts {0} {1} {2} {3} {4} {5} {6} {7} {8}'.format(meas_mode, stnry_en, low_pwr, loc_en, enc, leds, ble, uwb, fw_upd)
    serial_port.reset_input_buffer()
    cnt = 0
    for char in shell_cmd:
        # The decawave shell buffer only supports at most 6 characters to be inputted
        # at the same time. Extra characters need to be input with a pause. (by observation)
        if cnt != 6:
            serial_port.write(char.encode())
            cnt += 1
        else:
            time.sleep(0.1)
            serial_port.read(serial_port.in_waiting)
            cnt = 0
            serial_port.write(char.encode())
            cnt += 1
    serial_port.reset_input_buffer()
    serial_port.write(b'\x0D')
    time.sleep(1)
    ret = str(serial_port.read(serial_port.in_waiting))
    if "acts: ok" in ret:
        # the configuration is not guaranteed to be successful. 
        # Improvements/Retrials are needed to ensure the setup
        if reset:
            serial_port.write("reset".encode())
            serial_port.write(b'\x0D')
            sys.stdout.write(timestamp_log() + "tag configuration success, reset at trial time(s): {}, location engine set as {}\n".format(retrial_cnt, loc_en))
        return True
    sys.stdout.write(timestamp_log() + "tag configuration failed, retrying time(s): {}\n".format(retrial_cnt))
    if retrial_cnt == max_retrials:
        sys.stdout.write(timestamp_log() + "tag configuration failed after {} trial(s)\n".format(max_retrials))
        return False
    else:
        retrial_cnt += 1
        dwm_cfg_tag_set_shell_acts(serial_port=serial_port, 
                            loc_en=loc_en, max_retrials=max_retrials, retrial_cnt=retrial_cnt, 
                            meas_mode=meas_mode, stnry_en=stnry_en, low_pwr=low_pwr, enc=enc, 
                            leds=leds, ble=ble, uwb=uwb, fw_upd=fw_upd, reset=reset)


def accelerometer_init_shell_av(serial_port, max_retrials, retrial_cnt=0):
    """ Use shell command 'av' to initialize on-board LIS2DH12 accelerometer.
        'av' shell command execute built-in configurations processes that initialize LIS2DH12.
        only after executing 'av', the registers in LIS2DH12 will be able to reflect correct values.

        usage:
        av
        shell return sample: acc: x = 16336, y = 32, z = 1392
        
        :returns:
            True or False
    """
    shell_cmd = 'av'
    serial_port.reset_input_buffer()
    
    serial_port.write(shell_cmd.encode())
    serial_port.write(b'\x0D')
    time.sleep(1)
    ret = str(serial_port.read(serial_port.in_waiting))
    if "acc: x =" in ret:
        # the configuration is not guaranteed to be successful. 
        # Improvements/Retrials are needed to ensure the setup
        sys.stdout.write(timestamp_log() + "accelerometer init success\n")
        return True
    sys.stdout.write(timestamp_log() + "accelerometer init failed, retrying time(s): {}\n".format(retrial_cnt))
    if retrial_cnt == max_retrials:
        sys.stdout.write(timestamp_log() + "accelerometer init failed after {} trial(s)\n".format(max_retrials))
        return False
    else:
        retrial_cnt += 1
        accelerometer_init_shell_av(serial_port=serial_port, max_retrials=max_retrials, retrial_cnt=retrial_cnt)

if __name__ == "__main__":
    t = serial.Serial('COM6', baudrate=115200, timeout=3.0)
    from tag_mqtt_publisher_proxi_sensor_lcd import get_sys_info, report_uart_data
    proximity_pointer = [None]
    uwb_pointer = [None]
    report_uart_data(t, uwb_pointer, proximity_pointer, init=False, tag_id='0C0C')
    


import os, platform, sys

import serial, glob, re
import time
from datetime import datetime

import subprocess, atexit, signal
import paho.mqtt.client as mqtt

from proximity_sensor import proximity_init, proximity_start
from lcd import lcd_init, lcd_disp

import json, threading

from utils import *

# Constants for the MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883


def mqtt_on_publish(client, data, result):
    # TODO: Define actions to take if mqtt_on_publish is needed
    pass
    
def report_uart_data(serial_port, uwb_pointer, proximity_pointer):
    # uwb_pointer[0] is the pointer used to pass the coordinates and other UWB readings to other threads
    # proximity_pointer[0] passes the proximity sensor data acquired in a separate thread
    sys_info = parse_uart_sys_info(serial_port, oem_firmware=True)
    tag_id = sys_info.get("device_id") 
    upd_rate = sys_info.get("upd_rate")
    # type "lec\n" to the dwm shell console to activate data reporting
    if not is_reporting_loc(serial_port, timeout=upd_rate/10):        
        write_shell_command(serial_port, command=b'\x6C\x65\x63\x0D')
    assert is_reporting_loc(serial_port, timeout=upd_rate/10)
    
    # location data flow is confirmed. Start publishing to localhost (MQTT)
    sys.stdout.write(timestamp_log() + "Connecting to Broker...\n")
    tag_client = mqtt.Client("Tag:"+tag_id)
    # tag_client.on_publish = mqtt_on_publish
    tag_client.connect(MQTT_BROKER, MQTT_PORT)
    sys.stdout.write(timestamp_log() + "Connected to Broker! Publishing\n")
    serial_port.reset_input_buffer()

    super_frame = 0
    while True:
        try:
            data = str(serial_port.readline(), encoding="UTF-8").rstrip()
            if not data[:4] == "DIST":
                continue            
            json_dic = make_json_dict_oem(data)
            json_dic['tag_id'] = tag_id
            json_dic['superFrameNumber'] = super_frame
            # pass in the proximity reading using proximity_pointer[0] pointer from proximity thread
            json_dic['proximity'] = proximity_pointer[0] if proximity_pointer[0] is not None else "OutOfRange"
            json_data = json.dumps(json_dic)
            tag_client.publish("Tag/{}/Uplink/Location".format(tag_id[-4:]), json_data, qos=0, retain=True)
            super_frame += 1
            # pass out coordinates using uwb_pointer[0] pointer for other threads
            uwb_pointer[0] = json_dic
        except Exception as exp:
            data = str(serial_port.readline(), encoding="UTF-8").rstrip()
            sys.stdout.write(timestamp_log() + data)
            raise exp
    
    
# thread used for proximity sensor controlling and data reading
def proximity_thread_job(threshold, interval, timeout, proximity_pointer):
    # modifies proximity_pointer[0] and referred from the main thread to publish into MQTT
    # GPIO Pins (BCM) for proximity sensor
    TRIG=26
    ECHO=16
    PROXI=threshold
    INTERVAL=interval
    TIMEOUT=timeout
    startt = time.time()
    try:
        proximity_init(trig=TRIG, echo=ECHO)
        while True:
            dist = proximity_start(trig=TRIG, echo=ECHO, proximity_threshold=PROXI, timeout=TIMEOUT)
            time.sleep(INTERVAL)
            proximity_pointer[0] = dist
    except BaseException as e:
        raise(e)


# thread used for LCD displaying
def lcd_thread_job(data_pointer):
    # reads elements in data_pointer and proximity_pointer[0] and show them on the LCD
    try:
        lcd_init()
        while True:
            if data_pointer[0] is None:
                continue
            proxi = data_pointer[0].get("proximity", None)
            coords = data_pointer[0].get('est_pos', None)
            if proxi and coords:
                line1 = "Proxi: {} cm".format(proxi) if proxi is not None else "Proxi:OutOfRange"
                line2 = "x:{:.2f} y:{:.2f} m".format(coords['x'], coords['y'])
                lcd_disp(line1, line2)
            
    except BaseException as e:
        raise(e)


if __name__ == "__main__":
    sys.stdout.write(timestamp_log() + "MQTT publisher service started. PID: {}\n".format(os.getpid()))
    com_ports = get_tag_serial_port()
    tagport = com_ports.pop()
    assert len(com_ports) == 0
    
    # Initialize the serial (UART) port communicating with GPIO-mounted Decawave
    # In Python the readline timeout is set in the serialport init part
    t = serial.Serial(tagport, baudrate=115200, timeout=3.0)
    
    proximity_pointer = [None]
    uwb_pointer = [None]
    proximity_threshold, interval, timeout = 25, 0.5, 2
    
    proximity_thread = threading.Thread(target=proximity_thread_job, 
                                        args=(proximity_threshold, interval, timeout, proximity_pointer,),
                                        name="Proximity Sensor")
    proximity_thread.daemon = True
    proximity_thread.start()
    lcd_thread = threading.Thread(target=lcd_thread_job, 
                                    args=(uwb_pointer,),
                                    name="LCD")
    lcd_thread.daemon = True
    lcd_thread.start()
    port_available_check(t)
    try:
        parse_uart_init(t)
    except BaseException as e:
        sys.stdout.write(timestamp_log() + "Initialization failed. \n")
        raise e
    try:
        report_uart_data(t, uwb_pointer, proximity_pointer)
    except BaseException as e:
        sys.stdout.write(timestamp_log() + "Reporting process failed. \n")
        raise e
        sys.exit()

     


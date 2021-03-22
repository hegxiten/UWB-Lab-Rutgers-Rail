import os, sys
import RPi.GPIO as GPIO
import time
from datetime import datetime

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
TRIG=26
ECHO=16

PROXI=25
INTERVAL=0.5
TIMEOUT=2
# 15 CM as the maximum threshold for proximity detection


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

def proximity_init(trig=TRIG, echo=ECHO):
    sys.stdout.write(timestamp_log() + "Distance Measurement Started\n")
    GPIO.setup(trig, GPIO.OUT)
    GPIO.setup(echo, GPIO.IN)

def proximity_start(trig=TRIG, echo=ECHO, proximity_threshold=PROXI, timeout=TIMEOUT):
    GPIO.output(trig, False)
    time.sleep(0.00001)

    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    pulse_duration_threshold = proximity_threshold / 17150
    timeout_start = time.time()
    while GPIO.input(echo)==0:
        timeout_monitor = time.time()
        if timeout_monitor - timeout_start > timeout:
            return -1

    pulse_start = time.time()
    pulse_end = pulse_start
    PROX_FLAG = 1
    while GPIO.input(echo)==1:
        pulse_end = time.time()
        if pulse_end - pulse_start > pulse_duration_threshold:
            PROX_FLAG = 0
            break
    
    if PROX_FLAG:
        pulse_duration = pulse_end - pulse_start
        dist = pulse_duration * 17150
        dist = round(dist, 2)
        return dist
    else:
        return None
if __name__ == "__main__":
    startt = time.time()
    try:
        proximity_init()
        while True:
            dist = proximity_start()
            if not dist:
                sys.stdout.write(timestamp_log() + "Non in the range, greater than 15cm\n")
            else:
                sys.stdout.write(timestamp_log() + "Distance: {} cm\n".format(dist))
            time.sleep(INTERVAL)
    except BaseException as e:
        raise(e)
    finally:
        stopt = time.time()
        sys.stdout.write(timestamp_log() + "program running time: {} seconds".format(stopt - startt))
        GPIO.cleanup()
  

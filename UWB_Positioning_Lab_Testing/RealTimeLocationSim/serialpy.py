import time
import serial

"""
Sample code of loading UART DWM data input from serial connections
usage: 
    change the COM_PORT accordingly to the correct port connecting to the
    passive lister.
"""

COM_PORT = 'COM9'
try:
    ser = serial.Serial()
    ser.port = COM_PORT
    ser.baudrate = 115200
    ser.bytesize = serial.EIGHTBITS 
    ser.parity =serial.PARITY_NONE 
    ser.stopbits = serial.STOPBITS_ONE 
    ser.timeout = 1
    ser.open()
    ser.write(b'\r\r')
    time.sleep(1)
    ser.write(b'lep\r')
    ser.close()
except Exception as e:
    print(e)
    pass
print(ser)

ser.open()

while True:
    try:
        data=str(ser.readline())
        print(data)
        time.sleep(0.1)
    except KeyboardInterrupt:
        ser.close()
        pass
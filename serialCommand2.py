import serial
from ps4 import PyPS4
import datetime

ser = serial.Serial('/dev/ttyACM0')  # open serial port

lastMessageSent = datetime.datetime.now()
sent = False
stateCache = None
started = True
def cb(_data):
    global lastMessageSent, sent, started
    if _data[0]=="axes" and started is True:
        data = _data[1]
        deltaMillis = (datetime.datetime.now() - lastMessageSent).total_seconds() * 1000
        stateCache = data
        if (deltaMillis > 100) or sent is False:
            print(("writing data",data))
            ser.write(stateCache)
            lastMessageSent = datetime.datetime.now()
            sent = True
    elif _data[0]=="button":
        data = _data[1]

pyps4 = PyPS4(_cb=cb)
pyps4.start()
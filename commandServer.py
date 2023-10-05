

import socket
import json
import struct
import math
import serial

# i listen on port 5000 and send commands to the ard
myIp = "127.0.0.1"
myPort = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
sock.bind((myIp, myPort))
# open serial port
ser = serial.Serial('/dev/ttyACM0') 

#{'ljx': -6419}}, {'ljy': 0, 'ljx': -6419, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6081}}, {'ljy': 0, 'ljx': -6081, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6419}}, {'ljy': 0, 'ljx': -6419, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6081}}, {'ljy': 0, 'ljx': -6081, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6419}}, {'ljy': 0, 'ljx': -6419, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6081}}, {'ljy': 0, 'ljx': -6081, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6419}}, {'ljy': 0, 'ljx': -6419, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6081}}, {'ljy': 0, 'ljx': -6081, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6419}}, {'ljy': 0, 'ljx': -6419, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6081}}, {'ljy': 0, 'ljx': -6081, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6419}}, {'ljy': 0, 'ljx': -6419, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6081}}, {'ljy': 0, 'ljx': -6081, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6419}}, {'ljy': 0, 'ljx': -6419, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6081}}, {'ljy': 0, 'ljx': -6081, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6419}}, {'ljy': 0, 'ljx': -6419, 'rt': 207})
#({'type': 'axes', 'value': {'ljx': -6081}}, {'ljy': 0, 'ljx': -6081, 'rt': 207})

def printNByte(target, n):
    return ((target&(0xFF<<(8*n)))>>(8*n)) # hex

axisMaxValue = 32767
def normaliseProfile(roll, pitch, thrust):
    global axisMaxValue
    # normalise between -1 to 1 on
    normRoll = roll / axisMaxValue
    normPitch = pitch / axisMaxValue
    # project inside a unit circle using elipse formula
    normRollAuthorityAdjusted = normRoll * math.sqrt(1 - ((normPitch * normPitch)/2)) 
    normPitchAuthorityAdjusted = normPitch * math.sqrt(1 - ((normRoll * normRoll)/2))
    return (normRollAuthorityAdjusted, normPitchAuthorityAdjusted, thrust)

def createArdByteString(roll, pitch, thrust):
    binaryString = bytes([thrust])
    binaryString = binaryString + struct.pack("<ff", roll, pitch)
    return binaryString 

nullProfile = createArdByteString(0, 0, 0)
def performStateChange(stateChange):
    if stateChange["type"] == "axes":
        value = stateChange["value"]
        #create binary profile
        (roll, pitch, thrust) = normaliseProfile(value["ljx"], value["ljy"], value["rt"])
        profile = createArdByteString(pitch, roll, thrust)
        if thrust == 0:
            return
        if thrust < 20:
            profile = createArdByteString(roll, pitch, 20)
        ser.write(profile)
        print(("profile", profile, len(profile)))
    else:
        if stateChange["value"] == "x":
            ser.write(nullProfile)
            print(("profile", nullProfile))
        elif stateChange["value"] == "t":
            startProfile = createArdByteString(0, 0, 20)
            ser.write(startProfile)
            print(("profile", startProfile))
    print(stateChange)

while True:
    data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
    jsonProfile = json.loads(data)
    performStateChange(jsonProfile)
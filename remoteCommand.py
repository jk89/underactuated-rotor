from ps4 import PyPS4
import datetime
import socket
import json

# i decode the ps4 profile and sent it to 5000,5001
graphServer = ("127.0.0.1", 5001)
commandServer = ("127.0.0.1", 5000)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def sendCommands(stateChange):
    # encode message
    binaryJSONMessage = json.dumps(stateChange).encode('ascii')
    sock.sendto(binaryJSONMessage, commandServer)
    sock.sendto(binaryJSONMessage, graphServer)

axisChangeTolerance = {} #{'ljx': 500, 'ljy': 500, 'rt': 4}
normalAxisWithoutTolerance = ['ljx', 'ljy', 'rt']
lastMessageSent = datetime.datetime.now()

oldAxisState = None
def cb(data, axisState):
    global oldAxisState, lastMessageSent
    stateChange = None
    print((data,pyps4.axisState))
    if data["type"] == "button":
        stateChange = data
    else:
        if oldAxisState is not None:
            for key in normalAxisWithoutTolerance:
                if oldAxisState[key] != axisState[key]:
                    stateChange = {"type":"axes", "value": axisState}
                    continue
            if stateChange is None:
                for key in axisChangeTolerance.keys():
                    neededChange = axisChangeTolerance[key]
                    if (abs(oldAxisState[key] - axisState[key]) >= neededChange):
                        stateChange = {"type":"axes", "value": axisState}
                        continue
    if stateChange is not None:
        timeSinceLast = ((((datetime.datetime.now() - lastMessageSent).total_seconds() * 1000)))
        if (timeSinceLast > 45):
            sendCommands(stateChange)
        else:
            stateChange = None
    newOldState = False
    if oldAxisState is None:
        oldAxisState = {}
        newOldState = True
    if newOldState is True or stateChange is not None:
        for axisKey in axisState.keys():
            oldAxisState[axisKey] = axisState[axisKey]
        lastMessageSent = datetime.datetime.now()

pyps4 = PyPS4(_cb=cb)
pyps4.start()
import numpy as np 
from bokeh.plotting import curdoc, figure
from bokeh.models import ColumnDataSource, Range1d
from bokeh.layouts import column, row
import socket
import json

PI  = 3.1415926535897932384626433832795
fullCycle = 2 * PI
nBLDCCycles = 7
motorStepMod = nBLDCCycles * 6
step_angle = fullCycle / motorStepMod
pwmMaxDuty = 255
myIp = "127.0.0.1"
myPort = 5001

# i listen on port 5001 and graph the profile
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
sock.bind((myIp, myPort))

sinComp = []
cosComp = []
import math
def buildAngleTables():
    for i in range(motorStepMod):
        angle = step_angle * i
        sinComp.append(math.sin(angle))
        cosComp.append(math.cos(angle))

buildAngleTables()
axesTotal = 65534
singleAxesTotal = 32767
normMaxMagnitude = math.sqrt(0.5)

def computeDutyCycleCycle(pitch, roll, nDutyTarget):
    global sinComp, cosComp, axesTotal, counts
    step=[]
    duty=[]
    minThrust = 10000000000000
    maxThrust = 0
    counts = [nDutyTarget]

    normRoll = roll / singleAxesTotal
    normPitch = pitch / singleAxesTotal
    
    # map square to circle
    normRollAuthorityAdjusted = normRoll * math.sqrt(1 - ((normPitch * normPitch)/2))
    normPitchAuthorityAdjusted = normPitch * math.sqrt(1 - ((normRoll * normRoll)/2))
    # https://stackoverflow.com/questions/59505221/sending-floats-as-bytes-over-serial-from-python-program-to-arduino

    for i in range(motorStepMod):
        step.append(i * step_angle)
        nPitch = normPitchAuthorityAdjusted
        nRoll = normRollAuthorityAdjusted
        dutyAvailable = min(pwmMaxDuty - nDutyTarget, nDutyTarget)
        sinComponent = sinComp[i]
        cosComponent = cosComp[i]
        sinCompL = nRoll * dutyAvailable *  sinComponent
        cosCompL = nPitch * dutyAvailable * cosComponent
        thrust =  round(sinCompL + cosCompL + nDutyTarget)
        duty.append(thrust)
        if thrust > maxThrust:
            maxThrust = thrust
        if minThrust > thrust:
            minThrust = thrust
    pass
    x = step
    y = duty
    return (x, y, maxThrust - minThrust, normPitchAuthorityAdjusted, normRollAuthorityAdjusted)

x = None
y = None
plotData = ColumnDataSource(dict(x=[],y=[]))
coordinateData = ColumnDataSource(dict(x=[],y=[]))
originalCoordinateData = ColumnDataSource(dict(x=[],y=[]))

doc = curdoc()

def update():
    global x, y, doc, counts, thrustHist, colors
    data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
    jsonProfile = json.loads(data)
    print(jsonProfile)
    if jsonProfile["type"] == "button":
        if (jsonProfile["value"] == "x"):
            ljx = 0
            ljy = 0
            rt = 0
        elif (jsonProfile["value"] == "t"):
            ljx = 0
            ljy = 0
            rt = 20
    else:
        ljx = jsonProfile["value"]["ljx"] # roll
        ljy = jsonProfile["value"]["ljy"] # pitch
        rt = jsonProfile["value"]["rt"] # thrust
    print(("profile", jsonProfile["value"]))
    (x,y, authority, normPitch, normRoll) = computeDutyCycleCycle(ljy, ljx, rt)
    print("authority", round((authority * 100)/pwmMaxDuty, 2), "%")
    if (x is not None and y is not None):
        plotData.stream({'x': x, 'y': y}, rollover=motorStepMod)
        coordinateData.stream({"x": [normRoll], "y": [normPitch]}, rollover=1)
        originalCoordinateData.stream({"x": [ljx], "y": [ljy]}, rollover=1)
        updateThrust = {'x':thrustCategories,'y': counts, 'color': colors}
        thrustHist.data = updateThrust        
    doc.add_next_tick_callback(update)

p = figure(title="Duty[unit] vs Angle[rad]")
p2 = figure(title="Normalised Elliptical Coordinates (x, y)")
p3 = figure(title="Original PS4 Coordinates (x, y)")

left, right, bottom, top = -1, 1, -1, 1
p2.x_range=Range1d(left, right)
p2.y_range=Range1d(bottom, top)

left, right, bottom, top = -singleAxesTotal, singleAxesTotal, -singleAxesTotal, singleAxesTotal
p3.x_range=Range1d(left, right)
p3.y_range=Range1d(bottom, top)

r = p.circle(x='x', y='y', source=plotData)
c = p2.circle(x="x", y="y", source=coordinateData, line_width=10, line_color="#FF0000", fill_color="white")
o = p3.circle(x="x", y="y", source=originalCoordinateData, line_width=10, line_color="#00FF00", fill_color="white")

thrustCategories = ["consumedThrust"]
colors = ["#df4759"]
counts = [0]

thrustDict = {'x':thrustCategories,'y':counts, 'color': colors} 
thrustHist = ColumnDataSource(data=thrustDict)

p4 = figure(title="thrust level", x_range=thrustDict['x'])
p4.vbar(x='x', top='y', width=0.2, source=thrustHist, color='color', legend="x")
p4.xgrid.grid_line_color = None
p4.y_range.start = 0
p4.xgrid.grid_line_color = None
p4.y_range.start = 0

thrustBar = p4.vbar(x=thrustCategories, top=counts, width=0.9, color=colors)
docLayout = column(row(p3, p2, p4),row(p))
doc.add_root(docLayout)
doc.add_next_tick_callback(update)

#Telemetry mapper with MatPlotlib by Shoob V2 5/10/24

import time
import krpc
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from haversine import haversine, Unit
from multiprocessing import Process
import keyboard

#connect to kRPC
conn = krpc.connect(
    name='Telemetry_Test',
    address='192.168.1.154',
    rpc_port=50000, stream_port=50001
)

#define static objects
vessel = conn.space_center.active_vessel
flightInfo = vessel.flight()
referenceFrame = vessel.orbit.body.reference_frame

#DEFINE FLIGHT DATA STREAMS
MET = conn.add_stream(getattr, vessel, 'met')

altitude = conn.add_stream(getattr, vessel.flight(), 'surface_altitude')
speed = conn.add_stream(getattr, vessel.flight(referenceFrame), 'speed')

velocity = conn.add_stream(getattr, vessel.flight(referenceFrame), 'velocity')

qForce = conn.add_stream(getattr, vessel.flight(), 'dynamic_pressure')
vesselMach = conn.add_stream(getattr, vessel.flight(), 'mach')

vesselPitch = conn.add_stream(getattr, vessel.flight(), 'pitch')
vesselYaw = conn.add_stream(getattr, vessel.flight(), 'heading')
vesselRoll = conn.add_stream(getattr, vessel.flight(), 'roll')

latitude = conn.add_stream(getattr, vessel.flight(), 'latitude')
longitude = conn.add_stream(getattr, vessel.flight(), 'longitude')

mass = conn.add_stream(getattr, vessel, 'mass')
#start defining arrays

mett = [] #all MET points
met = [0] * 60 #last 60 MET points

alt = []
spd = []
        
velocityArr = [0,0]
metArr = [0,0]

#q/mach
q = []
m = []

#pyr
p = [0] * 60
ya = [0] * 60
r = [0] * 60

#acceleration x/y/z
x = [0] * 60
y = [0] * 60
z = [0] * 60

#velocity x/y/z
vx = [0] * 60
vy = [0] * 60
vz = [0] * 60


#define initial coords
startCoords = [28.54907,-80.65593] #KSC Coords
coords = [28.54907,-80.65593]
range = []

#start drawing plots
fig = plt.figure(layout="constrained")
axs = fig.subplot_mosaic([  ['00', '10', '20'],
                            ['00', '10', '20'],
                            ['00', '10', '20'],
                            ['01', '11', '21'],
                            ['02', '12', '22'],
                            ['03', '13', '23']],   
                            )

def initPlot():
    #00 - Altitude
    color = 'tab:red'
    axs['00'].set_title('Altitude and Speed')
    axs['00'].set_xlabel('Time (s)', color='black')
    axs['00'].set_ylabel('Altitude (m)', color=color)
    axs['00'].tick_params(axis='y', labelcolor=color)

    #001 - Speed (Subplot of Altitude)
    color = 'tab:blue'
    axs['001']=axs['00'].twinx()
    axs['001'].tick_params(axis='y', labelcolor=color)
    axs['001'].set_ylabel('Speed (m/s)', color=color)

    #10 - Dynamic Pressure
    color = 'tab:green'
    axs['10'].set_title('Dynamic Pressure (Pascals) and Mach (M)')
    axs['10'].set_xlabel('MET (s)', color='black')
    axs['10'].set_ylabel('Q (Pascals)', color=color)
    axs['10'].tick_params(axis='y', labelcolor=color)

    #101 - Mach (Subplot of Dynamic Pressure)
    color = 'tab:purple'
    axs['101']=axs['10'].twinx()
    axs['101'].tick_params(axis='y', labelcolor=color)
    axs['101'].set_ylabel('Mach (M)', color=color)

    #20 - Downrange Distance
    color = 'tab:red'
    axs['20'].set_title('Downrange Distance')
    axs['20'].set_xlabel('Downrange Distance (km)', color='black')
    axs['20'].set_ylabel('Altitude (m)', color='black')
    axs['20'].tick_params(axis='y', labelcolor='black')

    #01 - Acceleration (x)
    axs['01'].set_title('Acceleration (x)')
    axs['01'].set_xlabel('MET 60 (s)', color='black')
    axs['01'].set_ylabel('Acceleration (m/s)', color='black')
    axs['01'].autoscale(enable=True, axis='y')

    #02 - Acceleration (y)
    axs['02'].set_title('Acceleration (y)')
    axs['02'].set_xlabel('MET 60 (s)', color='black')
    axs['02'].set_ylabel('Acceleration (m/s)', color='black')
    axs['02'].autoscale(enable=True, axis='y')

    #03 - Acceleration (z)
    axs['03'].set_title('Acceleration (z)')
    axs['03'].set_xlabel('MET 60 (s)', color='black')
    axs['03'].set_ylabel('Acceleration (m/s)', color='black')
    axs['03'].autoscale(enable=True, axis='y')

    #11 - Velocity (x)
    axs['11'].set_title('Velocity (x)')
    axs['11'].set_xlabel('MET 60 (s)', color='black')
    axs['11'].set_ylabel('Velocity (m/s)', color='black')
    axs['11'].autoscale(enable=True, axis='y')

    #12 - Velocity (y)
    axs['12'].set_title('Velocity (y)')
    axs['12'].set_xlabel('MET 60 (s)', color='black')
    axs['12'].set_ylabel('velocity (m/s)', color='black')
    axs['12'].autoscale(enable=True, axis='y')

    #13 - Velocity (z)
    axs['13'].set_title('Velocity (z)')
    axs['13'].set_xlabel('MET 60 (s)', color='black')
    axs['13'].set_ylabel('Velocity (m/s)', color='black')
    axs['13'].autoscale(enable=True, axis='y')

    #21 - Pitch 
    axs['21'].set_title('Pitch')
    axs['21'].set_xlabel('MET 60 (s)', color='black')
    axs['21'].set_ylabel('Pitch (°)', color='black')
    axs['21'].set_ylim(-90,90)  
    axs['21'].set_yticks([-90,-45,0,45,90])

    #22 - Yaw
    axs['22'].set_title('Yaw')
    axs['22'].set_xlabel('MET 60 (s)', color='black')
    axs['22'].set_ylabel('Yaw (°)', color='black')
    axs['22'].set_ylim(0,360)
    axs['22'].set_yticks([0,90,180,270,360])

    #23- Roll
    axs['23'].set_title('Roll')
    axs['23'].set_xlabel('MET 60 (s)', color='black')
    axs['23'].set_ylabel('Roll (°)', color='black')
    axs['23'].set_ylim(-180,180)
    axs['23'].set_yticks([-180,-90,0,90,180])

initPlot()

def update():
    if MET() > 0:
        #calculate time since last MET tick
        metArr.pop(0)
        metArr.insert(1,MET())
        metDiff=np.subtract(metArr[1],metArr[0])

        #velocity comparison for dv-dt for acceleration calcs
        velocityArr.pop(0)
        velocityArr.insert(1,velocity())
        acc=np.subtract(velocityArr[1], velocityArr[0])/metDiff

        #mett is all MET ticks and met is last 60
        met.append(round(MET(),1))
        mett.append(round(MET(),1))

        #altitude and speed
        alt.append(round(altitude(),1))
        spd.append(round(speed(),2))

        #Q and Mach
        q.append(round(qForce(),1))
        m.append(round(vesselMach(),1))

        #PYR
        p.append(round(vesselPitch(),1))
        ya.append(round(vesselYaw(),1))
        r.append(round(vesselRoll(),1))

        #acceleration
        x.append(acc[0])
        y.append(acc[1])
        z.append(acc[2])

        #velocity
        vx.append((velocityArr[1])[0])
        vy.append((velocityArr[1])[1])
        vz.append((velocityArr[1])[2]*-1)

        #calculate current coordinates and downrange distance based off of it
        coords.append([round(latitude(),5),round(longitude(),5)])
        range.append(round(haversine(startCoords,coords[-1]),1))

        #axis plots
        axs['00'].plot(mett,alt, label='Altitude', color='red')
        axs['001'].plot(mett,spd, label='Speed (m/s)', color='blue')

        axs['10'].plot(mett,q, label='Q', color='green')
        axs['101'].plot(mett,m, label='Mach', color='purple')

        axs['20'].plot(range,alt, label='Downrange', color='c')

        axs['01'].plot(met,x, label='Acceleration (x)', color='red')
        axs['01'].set_xlim(met[-60],met[-1])

        axs['02'].plot(met,y, label='Acceleration (y)', color='#f93800')
        axs['02'].set_xlim(met[-60],met[-1])

        axs['03'].plot(met,z, label='Acceleration (z)', color='#ffb500')
        axs['03'].set_xlim(met[-60],met[-1])

        axs['11'].plot(met,vx, label='Velocity (x)', color='red')
        axs['11'].set_xlim(met[-60],met[-1])

        axs['12'].plot(met,vy, label='Velocity (y)', color='#f93800')
        axs['12'].set_xlim(met[-60],met[-1])

        axs['13'].plot(met,vz, label='Velocity (z)', color='#ffb500')
        axs['13'].set_xlim(met[-60],met[-1])

        axs['21'].plot(met,p, label='Pitch', color='red')
        axs['21'].set_xlim(met[-60],met[-1])

        axs['22'].plot(met,ya, label='Yaw', color='#f93800')
        axs['22'].set_xlim(met[-60],met[-1])

        axs['23'].plot(met,r, label='Roll', color='#ffb500')
        axs['23'].set_xlim(met[-60],met[-1])
        fig.canvas.draw_idle()

        if mass() == 0:
            print("Flight End. Press esc to continue...")
            keyboard.wait('esc')
            print("END")
            exit()
          
timer = fig.canvas.new_timer(interval=500)
timer.add_callback(update)
timer.start()


plt.show()


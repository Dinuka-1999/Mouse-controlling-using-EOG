import sys
import socket
import struct
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
import pyqtgraph as pg
import threading
import time
from scipy import signal
from scipy import ndimage


UDP_IP = "172.20.10.11" # The IP that is printed in the serial monitor from the ESP32
SHARED_UDP_PORT = 4210
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
sock.connect((UDP_IP, SHARED_UDP_PORT))

# Create the PyQtGraph application
app = QApplication([])
win = pg.GraphicsLayoutWidget(show=True)
show = [2,4]
plot=[]
orig_plot = []
baseLine_plot=[]
decision_plot=[]

for j,i in enumerate(show):
    plot.append(win.addPlot(title=f'Channel {i}'))
    # orig_plot.append(win.addPlot(title=f'Original {i}'))
    decision_plot.append(win.addPlot(title=f'Decision {i}'))
    # baseLine_plot.append(win.addPlot(title=f'base_Line {i}'))
    win.nextRow()

filtered_curve = []
orig_curve = []
baseLine_curve=[]
decision_curve=[]

color = ['b','g','r','c','b','g','r','c','b']
for i in range(len(show)):
    filtered_curve.append(plot[i].plot(pen='g'))
    orig_curve.append(plot[i].plot(pen='b'))
    baseLine_curve.append(plot[i].plot(pen='r'))
    decision_curve.append(decision_plot[i].plot(pen='r'))
    # baseLine_curve.append(plot[i].plot(pen='r'))

xdata = np.arange(1000)  # Number of data points to display on the plot
ydata = np.zeros((9,1000))
num_samples = 0
rate = 250

#     while True:
#         data = sock.recv(9*4)
#         print(data)

def loop():
    global ydata,num_samples
    while True:
        # Receive UDP packet
        data = sock.recv(4*9)
        # print(data)
        value = struct.unpack('iiiiiiiii', data)
        # print(value[2])

        for i in show:
            ydata[i][:-1] = ydata[i][1:]
            ydata[i][-1] = value[i]

        num_samples += 1

def update_plot():
    for i,j in enumerate(show):
        filtered_curve[i].setData(y=filtered[i])
        orig_curve[i].setData(y=ydata[j])
        baseLine_curve[i].setData(y=baseLine_filtered[i])
        decision_curve[i].setData(y=decision_arr[i])

def second_timer():
    global rate,num_samples
    while True:
        time.sleep(1)
        rate = num_samples
        num_samples = 0
        # print(rate)

difference=np.zeros((1,1000))

# def classify_signal():
#     global threshold1 , threshold2,decision_arr
#     decision_arr=np.zeros((2,1000))
#     difference=np.zeros((2,1000))
    
#     while True:
#         # for i,j in enumerate(show):
#         #     difference[i]=filtered[j]-baseLine_filtered[i]

#         difference=filtered-baseLine_filtered
#         arr1=(difference>1000).astype(int)
#         arr2=-(difference<-1000).astype(int)
#         print(arr1)

#         # if arr1[-1]==True:
#         #     decision_arr[-1]=1 
#         # elif arr2[-1]==True:
#         #     decision_arr[-1]=-1
#         # else:
#         #     decision_arr[-1]=0
#         decision_arr=arr1+arr2
#         # if len(decision_arr)==3:
#         #     if decision_arr==[1,0,0]:
#         #         print("blink")
#         #     elif decision_arr==[1,0,-1]:
#         #         print("up")
#         #     elif decision_arr==[-1,0,1]:
#         #         print("down")
#         #     decision_arr=[]


def filter():
    global rate, filtered, baseLine_filtered,decision_arr
    # bandpass = signal.butter(10, [0.2,40], 'bandpass', fs=rate, output='sos')

    while True:
        # highpass = signal.butter(10, 0.5, 'hp', fs=rate, output='sos')
        lowpass = signal.butter(30, 80, 'lp', fs=rate, output='sos')
        bandstop = signal.butter(10, [48,52], 'bandstop', fs=rate, output='sos')
        # baseLine_filter=signal.butter(10, 0.2, 'lp', fs=rate, output='sos')
        # ha,hb = signal.butter(10, 0.2, 'hp', fs=rate)
        # la,lb = signal.butter(10, 40, 'lp', fs=rate)

        # filtered = signal.sosfilt(bandpass, ydata)

        # filtered = signal.sosfilt(highpass, ydata)
        # remove average of ydata
        # print(np.mean(ydata,axis=1))
        # ydata_avg = ydata - np.mean(ydata,axis=1).reshape(-1,1)
        # print(ydata_avg.shape)
        # filtered1 = signal.sosfilt(bandstop, ydata_avg)
        # filtered = signal.sosfilt(lowpass, filtered1)
        filtered=np.zeros((2,ydata.shape[1]))
        for r,i in enumerate(show):
            filtered[r]=signal.medfilt(ydata[i], kernel_size=9)
            
        baseLine_filtered=np.zeros((2,ydata.shape[1]))
        for r,i in enumerate(show):
            baseLine_filtered[r]=signal.medfilt(ydata[i], kernel_size=151)
        # baseLine_filtered=signal.sosfilt(baseLine_filter, filtered)

        # filtered1 = signal.filtfilt(ha,hb,ydata)
        # filtered = signal.filtfilt(la,lb,filtered1)
        difference=filtered-baseLine_filtered
        threshold=2000
        arr1=(difference>threshold).astype(int)
        arr2=-(difference<-threshold).astype(int)

        # if arr1[-1]==True:
        #     decision_arr[-1]=1 
        # elif arr2[-1]==True:
        #     decision_arr[-1]=-1
        # else:
        #     decision_arr[-1]=0
        decision_arr=arr1+arr2

# Set up a timer to update the plot
timer = QtCore.QTimer()
timer.timeout.connect(update_plot)
timer.start(10*len(show))  # Update every 10 ms

if __name__ == "__main__":
    sock.send('Hello ESP32'.encode())
    t1 = threading.Thread(target=loop)
    t1.start()
    t2 = threading.Thread(target=second_timer)
    t2.start()
    t3 = threading.Thread(target=filter)
    t3.start()
    # t4 = threading.Thread(target=classify_signal)
    # t4.start()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
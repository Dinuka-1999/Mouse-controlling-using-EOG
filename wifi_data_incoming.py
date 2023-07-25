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
import pyautogui

UDP_IP = "172.20.10.11" # The IP that is printed in the serial monitor from the ESP32
SHARED_UDP_PORT = 4210
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
sock.connect((UDP_IP, SHARED_UDP_PORT))
trigger_sample=499
hori_Channel=2
verti_channel=3
# Create the PyQtGraph application
app = QApplication([])
win = pg.GraphicsLayoutWidget(show=True)
show = [2,3,4]
plot=[]
orig_plot = []
baseLine_plot=[]
decision_plot=[]

for j,i in enumerate(show):
    plot.append(win.addPlot(title=f'Channel {i}'))
    orig_plot.append(win.addPlot(title=f'Original {i}'))
    decision_plot.append(win.addPlot(title=f'Decision {i}'))
    # baseLine_plot.append(win.addPlot(title=f'base_Line {i}'))
    win.nextRow()

filtered_curve = []
orig_curve = []
baseLine_curve=[]
decision_curve=[]
upper_thresh_curve=[]
lower_thresh_curve=[]
color = ['b','g','r','c','b','g','r','c','b']
for i in range(len(show)):
    filtered_curve.append(plot[i].plot(pen='g'))
    orig_curve.append(orig_plot[i].plot(pen='b'))
    baseLine_curve.append(plot[i].plot(pen='r'))
    decision_curve.append(decision_plot[i].plot(pen='r'))
    upper_thresh_curve.append(plot[i].plot(pen='y'))
    lower_thresh_curve.append(plot[i].plot(pen='y'))
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
        orig_curve[i].setData(y=ydata_avg[j])
        filtered_curve[i].setData(y=filtered[i])
        baseLine_curve[i].setData(y=baseLine_filtered[i])
        decision_curve[i].setData(y=decision_arr[i])
        upper_thresh_curve[i].setData(y=upper_thresh[i])
        lower_thresh_curve[i].setData(y=lower_thresh[i])

def second_timer():
    global rate,num_samples
    while True:
        time.sleep(1)
        rate = num_samples
        num_samples = 0
        # print(rate)

def decision_take(decision,channel):
    decision_sample=decision[trigger_sample]
    if decision_sample!=0:
        # print(decision_sample)
        edges=np.diff(decision)
        # edges=np.zeros((1000))
        split_edges=edges[trigger_sample-9:trigger_sample+250]
        array_seq=split_edges[split_edges!=0].tolist()

        print(array_seq)
        if channel==verti_channel:
            if (array_seq==[-1,1,1,-1] or array_seq==[-1,1]):
                print("Eye down")
                #pyautogui.moveRel(0,-50, duration = 0.5)
            elif array_seq==[1,-1,-1,1]:
                print("Eye up")
                #pyautogui.moveRel(0, 50, duration = 1)
            elif array_seq==[1,-1]:
                print("Blink")
            else:
                print("try again")

        elif channel==hori_Channel:
            if (array_seq==[-1,1,1,-1] or array_seq==[-1,1]):
                print("Eye left")
               # pyautogui.moveRel(-50,0, duration = 0.5)
            elif (array_seq==[1,-1,-1,1] or array_seq==[1,-1]):
                print("Eye right")
               # pyautogui.moveRel(50,0, duration = 0.5)
            else:
                print("try again")

        time.sleep(1)

def classifier():
    time.sleep(1)
    while True:
        time.sleep(0.001)
        for r,i in enumerate(show):
            decision_take(decision_arr[r],i)

def filter():
    global rate, filtered, baseLine_filtered,decision_arr,ydata_avg,upper_thresh,lower_thresh,big_difference
    # bandpass = signal.butter(10, [0.2,40], 'bandpass', fs=rate, output='sos')
    upper_thresh=np.zeros((len(show),1000))
    lower_thresh=np.zeros((len(show),1000))
    big_difference=np.zeros((len(show),10000))
    while True:
    
        lowpass = signal.butter(30, 80, 'lp', fs=rate, output='sos')
        bandstop = signal.butter(10, [48,52], 'bandstop', fs=rate, output='sos')
        
        ydata_avg = ydata - np.mean(ydata,axis=1).reshape(-1,1)
        
        filtered1=np.zeros((len(show),ydata.shape[1]))
        for r,i in enumerate(show):
            filtered1[r] = signal.sosfilt(bandstop, ydata_avg[i])

        filtered2=np.zeros((len(show),ydata.shape[1]))
        for r,i in enumerate(show):
            filtered2[r] = signal.sosfilt(lowpass, filtered1[r])
            
        filtered=np.zeros((len(show),ydata.shape[1]))
        for r,i in enumerate(show):
            filtered[r]=signal.medfilt(filtered2[r], kernel_size=9)
            
        baseLine_filtered=np.zeros((len(show),ydata.shape[1]))
        for r,i in enumerate(show):
            baseLine_filtered[r]=signal.medfilt(filtered[r], kernel_size=151)

        difference=filtered-baseLine_filtered
        sd=np.std(big_difference,axis=1)
        k=3
        samp=baseLine_filtered[:,trigger_sample]

        upper_thresh[:,:]=baseLine_filtered+(k*sd).reshape(len(show),1)
        lower_thresh[:,:]=baseLine_filtered+(-k*sd).reshape(len(show),1)
        arr1=(difference>(samp+k*sd).reshape(len(show),1)).astype(int)
        arr2=-(difference<(samp-k*sd).reshape(len(show),1)).astype(int)

        decision_arr=arr1+arr2
        big_difference[:,:-1]=big_difference[:,1:]
        big_difference[:,-1]=difference[:,-1]
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
    t4 = threading.Thread(target=classifier)
    t4.start()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
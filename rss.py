import sys
import platform
import glob
import numpy.ma as ma
import numpy as np
import serial
import time
from struct import unpack


# ########################################
# Code to provide a fixed-length buffer data type
class FixedLenMaskedBuffer:
    def __init__(self, initlist, masked_value):
        self.frontInd = 0
        self.data     = ma.masked_equal(initlist, masked_value)
        self.len      = len(initlist)
    
    def list(self):
        oldest = self.frontInd+1
        return self.data[oldest:] + self.data[:oldest]
    
    # Append also deletes the oldest item
    def append(self, newItem):
        self.frontInd += 1
        if self.frontInd >= self.len:
            self.frontInd = 0
        self.data[self.frontInd] = newItem
    
    # Returns the "front" item
    def mostRecent(self):
        return self.data[self.frontInd]
    
    # Returns the N items most recently appended
    def mostRecentN(self,N):
        return [self.data[(self.frontInd-i)%self.len] for i in range(N-1,-1,-1)]
    
    # Returns the variance of the data
    def var(self):
        return np.var(self.data)    
# ########################################        
    
def run_sniffer():
    # Establish a serial connection and clear the buffer
    serial_filename = serialFileName()
    sys.stderr.write('Using USB port file: ' + serial_filename + '\n')
    ser = serial.Serial(serial_filename,38400)
    
    ser.flushInput()
    beef = '\xef' + '\xbe'
    buffer = ''
    
    node_list = []
    channel_list = []
    start_time = time.time()
    
    # Keep on listening for multi-Spin packets
    while time.time() < (start_time + 5.):
        buffer = buffer + ser.read(ser.inWaiting())
        if beef in buffer:
            lines = buffer.split(beef, 1)
            binaryPacket = lines[-2]
            buffer = lines[-1]
            spinPacket = unpack('<Hb' + (len(binaryPacket) - 4) * 'b' + 'b', binaryPacket)
    #         print(spinPacket)
    
            # Get the node_list
            if len(node_list) == 0:
                node_list.append(spinPacket[1])
            else:
                if (np.array(node_list) == spinPacket[1]).sum() == 0:
                    node_list.append(spinPacket[1])
            
            # Get the channel list
            if len(channel_list) == 0:
                channel_list.append(spinPacket[-2])
            else:
                if (np.array(channel_list) == spinPacket[-2]).sum() == 0:
                    channel_list.append(spinPacket[-2])
    
    ser.close()
    
    return (len(node_list),sorted(channel_list))




# Convert Tx, Rx, and Ch numbers to link number
def linkNumForTxRxChLists(tx, rx, ch, nodeList, channelList):
    if (nodeList.count(tx) == 0) or (nodeList.count(rx) == 0) or (channelList.count(ch) == 0):
        sys.stderr.write('Error in linkNumForTxRx: tx, rx, or ch number invalid')
    rx_enum = nodeList.index(rx)
    tx_enum = nodeList.index(tx)
    ch_enum = channelList.index(ch)
    nodes = len(nodeList)
    links = nodes*(nodes-1)
    linknum = ch_enum*links + tx_enum*(nodes-1) + rx_enum
    if (rx_enum > tx_enum):
        linknum -= 1
    return linknum

# Convert link number to Tx and Rx numbers
def txRxChForLinkNum(linknum, nodeList, channelList):
    nodes   = len(nodeList)
    links   = nodes*(nodes-1)
    ch_enum = linknum / links
    remLN   = linknum % links
    tx_enum = remLN / (nodes-1)
    rx_enum = remLN % (nodes-1)
    if (rx_enum >= tx_enum):
        rx_enum+=1
    if (tx_enum >= nodes) | (ch_enum > len(channelList)):
        sys.stderr.write('Error in txRxForLinkNum: linknum or ch too high for nodes, channels values')
    else:
        ch = channelList[ch_enum]
        tx = nodeList[tx_enum]
        rx = nodeList[rx_enum]
    return (tx, rx, ch)



def hex2signedint(he):
    # Convert from hexidecimal 2's complement to signed 8 bit integer
    return (int(he,16) + 2**7) % 2**8 - 2**7

def prevChannel(channelList, ch_now):
    if (channelList.count(ch_now) > 0):
        i = channelList.index(ch_now)
        rval = channelList[(i-1) % len(channelList)]
    else:
        rval = -1  # Key for bad ch_now input
    return rval

# USER: The following serial "file name" changes depending on your operating
#       system, and what name is assigned to the serial port when your listen
#       node is plugged in.
def serialFileName():    
    system_name = platform.system()
    #
    # LINUX USERS
    if system_name == 'Linux':
        # Automatically grab the USB filename (since the number after /dev/ttyACM may vary)
        usb_file_list = glob.glob('/dev/ttyACM*')
        if len(usb_file_list) > 0:
            serial_filename =  usb_file_list[0]  
        else:
            sys.stderr.write('Error: No Listen node plugged in?\n')
            serial_filename = '0'
    #
    # WINDOWS USERS: Change 'COM#' to match what the system calls your USB port.
    elif system_name == 'Windows':
        serial_filename = 'COM3'
    #
    # MAC USERS
    else:  # 'Darwin' indicates MAC OS X
        # Automatically grab the USB filename (since the number after /dev/tty.usb may vary)
        usb_file_list = glob.glob('/dev/tty.usb*')
        if len(usb_file_list) > 0:
            serial_filename =  usb_file_list[0]  
        else:
            sys.stderr.write('Error: No Listen node plugged in?\n')
    #
#    return '/dev/tty.usbmodem411'
#    return '/dev/tty.usbmodem621'
#    return '/dev/ttyACM0'
    return serial_filename


    

# This script reads packet data from the listen node through the serial port
# and prints one RSS measurement on each line for all tx, rx, ch combination,
# where the rx != tx, both rx and tx are in the list of sensors, and ch is in 
# the list of channels.
#
# Operation: Run this script in the terminal.  There are no command line parameters
# We assume that you are only using a 2 node setup.
# The channelList must match the channels that are programmed on the nodes
# You can also select which channels to plot using the ch_list.  Select any ordered numbers between 1 and the number of channels programmed on the nodes
# 
# 
#
# Version History:
#
# Version 1.1:  Initial Release, 27 Jan 2016
# 

import sys
import serial
import time
import rss as rss
import network_class_v1 as aNetwork
import rss_editor_class as aRssEdit
import myPlotter as aPlotter
import numpy as np


# What channels are measured by your nodes, in order of their measurement?
# USER:  SET THIS TO THE CHANNELS IN YOUR CHANNEL GROUP
# Input manually
# channelList   = [26, 11, 16, 21]
# maxNodes      = 2

# Automate process
print "Initializing..."
maxNodes,channelList = rss.run_sniffer()
print "Ready to plot."

# USER: The following serial "file name" changes depending on your operating 
#       system, and what name is assigned to the serial port when your listen 
#       node is plugged in.

serial_filename = rss.serialFileName()
sys.stderr.write('Using USB port file: ' + serial_filename + '\n')
ser = serial.Serial(serial_filename,38400)

# How many nodes the sensors have as the max # nodes (what # they're programmed with)
# USER:  THIS SHOULD NOT BE CHANGED, IT IS 6 FOR ALL GROUPS IN OUR CLASS


# What node numbers are yours, that you want to see output to the file.
# USER:  SET THIS TO THE NODE IDS ASSIGNED TO YOU.  DO NOT INCLUDE THE LISTEN NODE NUMBER
nodeList      = range(1,maxNodes+1)  # 1, ..., 30

# Parameters that are due to our implementation of the listen node.
numNodes      = len(nodeList)
numChs        = len(channelList)
numLinks      = numNodes*(numNodes-1)*numChs
rssIndex      = 3
string_length = maxNodes + 7
suffix        = ['ef','be']  # "0xBEEF"

# Initialize data, output file
nodeSet       = set(nodeList)
channelSet    = set(channelList)
currentLine   = []  # Init serial data buffer "currentLine" as empty.
currentLinkRSS = [127] * numLinks

###############################
# Set up network
###############################
node_locs = np.array([[0.,0.],[1.,1.]])
num_nodes = numNodes
num_ch = numChs
node_list = np.array([1,2])
ch_list = np.array([1,2])
link_order_choice = 'f'
myNetwork = aNetwork.aNetwork(node_locs, num_nodes, num_ch, node_list, ch_list, link_order_choice)

################################
# Set up RSS editor
################################
myRssEdit = aRssEdit.RssEditor(myNetwork)

################################
# Set up RSS editor
################################
num_samples = 80
plot_obj = aPlotter.MYPLOTTER(myRssEdit,num_samples)

# Run forever, adding one integer at a time from the serial port, 
#   whenever an integer is available.
while(1):
    tempInt = ser.read().encode('hex')
    currentLine.append(tempInt)
 
    # Whenever the end-of-line sequence is read, operate on the "packet" of data.
    if currentLine[-2:] == suffix:
        if len(currentLine) != string_length:
            sys.stderr.write('packet corrupted - wrong string length\n')
            del currentLine[:]
            continue
        currentLineInt = [int(x, 16) for x in currentLine]
        rxId = currentLineInt[2]
        currentCh = currentLineInt[-4]
 
        if (rxId not in nodeSet) or (currentCh not in channelSet):
            del currentLine[:]
            continue                    
         
        # Each line in the serial data has RSS values for multiple txids.
        # Output one line per txid, rxid, ch combo.
        for txId in nodeList:
            # If the rxId is after the txId, then no problem -- currentCh
            # is also the channel that node txId was transmitting on when
            # node rxId made the measurement, because nodes transmit on a
            # channel in increasing order.
            if rxId > txId: 
                ch = currentCh
            else: 
                ch = rss.prevChannel(channelList, currentCh)
             
            # If the link (tx, rx, ch) is one we are supposed to watch
            if txId != rxId:  
                i = rss.linkNumForTxRxChLists(txId, rxId, ch, nodeList, channelList)
                 
                # If the RSS has already been recorded for this link on 
                # this "line", then output the line first, and then restart 
                # with a new line.
                if currentLinkRSS[i] < 127:
                    cur_line = ' '.join(map(str,currentLinkRSS)) + ' ' + str(time.time()) + '\n'
                    myRssEdit.observe(cur_line)
                     
                    plot_obj.plot_current_image(myRssEdit.get_rss())
                     
                     
#                     sys.stdout.write(str(myRssEdit.get_rss().astype('int')) + '\n')
#                     sys.stdout.flush()
                     
                    # Output currentLinkRSS vector
                    # Restart with a new line by resetting currentLinkRSS
                    currentLinkRSS = [127] * numLinks
                 
                # Store the RSS 
                currentLinkRSS[i] = rss.hex2signedint(currentLine[rssIndex+txId-1])
 
        # Remove serial data from the buffer.
        currentLine = []
        

    
    

import time
import datetime
import serial
import sys
import platform
import glob

################################
# This class is responsible for reading in a new line 
# of RSS values and RIP band measurement.  When it goes from
# off to on, we initialize a file to save to, and continuously
# save the data to file.  When it goes from on to off, we close
# the file, and wait until the button is pressed again.
class rss_measurement():
    
    def __init__(self):
        self.fname = None
        self.f_out = None
        self.bbb_id = 'id1'
        self.__init_ser()
        
    # Initialize serial
    def __init_ser(self):    
        
        # Automatically grab the USB filename (since the number after /dev/ttyACM may vary)
        usb_file_list = glob.glob('/dev/ttyACM*')
        if len(usb_file_list) > 0:
            serial_filename =  usb_file_list[0]  
        else:
            sys.stderr.write('Error: No Listen node plugged in?\n')
            serial_filename = '0'
        
        self.ser = serial.Serial(serial_filename,38400)
        
    # Get previous channel
    def __prevChannel(self,channelList,ch_now):
        if (channelList.count(ch_now) > 0):
            i = channelList.index(ch_now)
            rval = channelList[(i-1) % len(channelList)]
        else:
            rval = -1  # Key for bad ch_now input
        return rval
    
    # Hex to signed int
    def __hex2signedint(self,he):
        # Convert from hexidecimal 2's complement to signed 8 bit integer
        return (int(he,16) + 2**7) % 2**8 - 2**7
    
    # Get the link number for a given tx, rx, ch
    def __linkNumForTxRxChLists(self,tx, rx, ch, nodeList, channelList):
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
        
    # Get the next file number
    def __get_next_file_name(self):
        # Get today's date
        td = datetime.datetime.today()
        
        # All files in the directory
        file_list = sorted(glob.glob("/root/spencer/clinical_data/rss*.txt"))
        
        # start the file name
        mm = str(td.month)
        if len(mm) == 1:
            mm = '0'+mm
        dd = str(td.day)
        if len(dd) == 1:
            dd = '0'+dd
        fname = '/root/spencer/clinical_data/rss_' + self.bbb_id + '_' + str(td.year) + '_' + mm + '_' + dd + '_'
        
        # If there are no files in the directory
        if len(file_list) == 0:
            return fname+'000.txt'
        
        # Loop through all the files and see if there is already a file
        # created on the same day as today
        for ii in range(len(file_list)-1,-1,-1):
            tmp_start = file_list[ii].split('/')[-1].split('_')[2:-1]
            tmp_end = [file_list[ii].split('/')[-1].split('_')[-1].split('.')[0]]
            tmp = tmp_start + tmp_end
            
            d0 = datetime.datetime(int(tmp[0]), int(tmp[1]), int(tmp[2]))
            delta = td-d0
            
            # if there is a file with the same day,
            # add one to the number of files for this day
            if delta.days == 0:
                # Add one to the number of files
                fnum = str(int(tmp[-1]) + 1)
                if len(fnum) == 1:
                    fnum = '00' + fnum
                if len(fnum) == 2:
                    fnum = '0' + fnum
                
                return fname + fnum + '.txt'
        
        # If we have arrived here, we haven't created any files on this day
        return fname + '000.txt'
    
    # observe a new line
    def observe(self):
        
        channelList   = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]

        # What node numbers are yours, that you want to see output to the file.
        # USER:  SET THIS TO THE NODE IDS ASSIGNED TO YOU.  DO NOT INCLUDE THE LISTEN NODE NUMBER
        nodeList      = range(1,3)  # 1, ..., 30
        
        # How many nodes the sensors have as the max # nodes (what # they're programmed with)
        # USER:  THIS SHOULD NOT BE CHANGED, IT IS 6 FOR ALL GROUPS IN OUR CLASS
        maxNodes      = 2
        
        # Parameters that are due to our implementation of the listen node.
        startTime     = time.time()
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
        
        # Find the last file number, and add one
#         self.fname = self.__get_next_file_name()
#         self.f_out = open(self.fname,'w')
        
        # Put in a header line
#         first_line = 'Started at: ' + str(datetime.datetime.now()) + '\n'
#         self.f_out.write(first_line)
        
        # Run forever, adding one integer at a time from the serial port, 
        #   whenever an integer is available.
        while(1):
            
            tempInt = self.ser.read().encode('hex')
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
                #print [currentLineInt[0:3], [hex2signedint(he) for he in currentLine[3:9]], currentLineInt[9:]]
                #print rxId
                if (rxId not in nodeSet) or (currentCh not in channelSet):
                    del currentLine[:]
                    continue
                timeStampSec = time.time()
                            
                
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
                        ch = self.__prevChannel(channelList, currentCh)
                    
                    # If the link (tx, rx, ch) is one we are supposed to watch
                    if txId != rxId:  
                        i = self.__linkNumForTxRxChLists(txId, rxId, ch, nodeList, channelList)
                        
                        # If the RSS has already been recorded for this link on 
                        # this "line", then output the line first, and then restart 
                        # with a new line.
                        if currentLinkRSS[i] < 127:
                            # Calc time in ms since start of script
                            timeDiff_ms = int((time.time() - startTime)*1000)
                            # Calc the ADC value of RIP belts
                            
                            # Output currentLinkRSS vector
                            sys.stdout.write(' '.join(map(str,currentLinkRSS)) + ' ' + str(timeDiff_ms) + '\n')
                            sys.stdout.flush()
                            
                            # Write to file
#                             self.f_out.write(' '.join(map(str,currentLinkRSS)) + ' ' + str(timeDiff_ms) + '\n')
                            
                            # If the button has been pressed, close the file and
                            # get out of observe.
#                             if not self.start_stop_obj.is_listen_state_on():
#                                 self.f_out.close()
#                                 return 0
                            
                            # Restart with a new line by resetting currentLinkRSS
                            currentLinkRSS = [127] * numLinks
                        
                        # Store the RSS 
                        currentLinkRSS[i] = self.__hex2signedint(currentLine[rssIndex+txId-1])
        
                # Remove serial data from the buffer.
                currentLine = []


################################
# Start of the main function

# Create start-stop object
my_rss_measurement_obj = rss_measurement()


# Loop forever
while True:
    my_rss_measurement_obj.observe()
#!/usr/bin/env python

# This script starts on bootup.  When a user pushes a button,
# this script starts the listen python script to collect data.
# When the script is running, the LED remains on.  When the user
# pushes the button again, the scripts stops and the LED turns 
# off.  It then waits until the user to push the button again
# to start the listen script again.

import Adafruit_BBIO.GPIO as GPIO
import signal
import logging
import logging.handlers
import argparse
import time
import datetime
import serial
import sys
import platform
import glob

# Define function to turn off leds gracefully
def Exit_gracefully(signal, frame):
    print "Closing..."
    sys.exit(0)

# Use a logging system to save the messages printed to stdout
# Deafults
LOG_FILENAME = "/root/spencer/clinical_data/myservice.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"
 
# Define and parse command line arguments
parser = argparse.ArgumentParser(description="My simple Python service")
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_FILENAME + "')")
 
# If the log file is specified on the command line then override the default
args = parser.parse_args()
if args.log:
    LOG_FILENAME = args.log
 
# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)
 
# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
    def __init__(self, logger, level):
        """Needs a logger and a logger level."""
        self.logger = logger
        self.level = level
 
    def write(self, message):
        # Only log if there is a message (not just a new line)
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())
 
# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)



# Start and Stop class.  This class is responsible for setting
# up the GPIO for the button and the LED.  It also is responsible
# for saving the state of if the listen script is running or not.
class start_stop():
    def __init__(self):
        self.gpio_button = "P9_11"
        self.gpio_led_listen = "P8_11"
        self.gpio_led_script = "P8_13"
        
        self.timer_start = 0.0
        
        self.old_button_state = 0
        self.new_button_state = 0
        self.listen_state = 0
        
        self.__init_pins()
    
    def __init_pins(self):
        GPIO.setup(self.gpio_button, GPIO.IN)
        GPIO.setup(self.gpio_led_listen, GPIO.OUT)
        GPIO.output(self.gpio_led_listen, GPIO.LOW)
        
        # Turn on the "Script is running LED"
        GPIO.setup(self.gpio_led_script,GPIO.OUT)
        GPIO.output(self.gpio_led_script, GPIO.LOW)
        GPIO.output(self.gpio_led_script,GPIO.HIGH)
    
    # Turn on the LED  
    def __turn_on_led(self):
        GPIO.output(self.gpio_led_listen,GPIO.HIGH)
    
    # Turn off the LED
    def __turn_off_led(self):
        GPIO.output(self.gpio_led_listen,GPIO.LOW)
    
    # Determine if the current observed button value constitutes a valid button
    # press
    def __is_valid_button_press(self):
        return (time.time() - self.timer_start) >= 3.0
    
    # Returns 1 if we went from low to high
    def __from_low_to_high(self):
        if self.old_button_state == 0 and self.new_button_state == 1:
            return 1
        else:
            return 0
    
    # Returns 1 if we went from high to low
    def __from_high_to_low(self):
        if self.old_button_state == 1 and self.new_button_state == 0:
            return 1
        else:
            return 0
    
    # Returns 1 if we stayed high
    def __stayed_high(self):
        if self.old_button_state == 1 and self.new_button_state == 1:
            return 1
        else:
            return 0
            
    # Get the current 
    def __get_button_state(self):
        self.old_button_state = self.new_button_state
        self.new_button_state = GPIO.input(self.gpio_button)        
        
    # This method observes the incoming GPIO signal and decides if we should
    # toggle the listen state and the LED.
    def observe(self):
        
        # Get the new button state, and update the old state
        self.__get_button_state()
        
        # If the listen script is off
        if self.listen_state == 0:
            
            if self.__from_low_to_high():
                # Start timer
                self.timer_start = time.time()
                print "Timer started from off..." + str(time.time())
                
            elif self.__stayed_high():
                if self.timer_start != 0.0:
                    if self.__is_valid_button_press():
                        self.listen_state = 1
                        self.__turn_on_led()
                        self.timer_start = 0.0
            
            elif self.__from_high_to_low():
                self.timer_start = 0.0
                
        # if the listen script is on
        else:
             
            if self.__from_low_to_high():
                # Start timer
                self.timer_start = time.time()
                print "Timer started from on..." + str(time.time())
                
            elif self.__stayed_high():
                if self.timer_start != 0.0:
                    if self.__is_valid_button_press():
                        self.listen_state = 0
                        self.__turn_off_led()
                        self.timer_start = 0.0
            
            elif self.__from_high_to_low():
                self.timer_start = 0.0
                
    def is_listen_state_on(self):
        if self.listen_state == 1:
            return 1
        else:
            return 0
        
################################
# This class is responsible for reading in a new line 
# of RSS values and RIP band measurement.  When it goes from
# off to on, we initialize a file to save to, and continuously
# save the data to file.  When it goes from on to off, we close
# the file, and wait until the button is pressed again.
class rss_measurement():
    
    def __init__(self,start_stop_obj):
        self.start_stop_obj = start_stop_obj
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
        self.fname = self.__get_next_file_name()
        self.f_out = open(self.fname,'w')
        
        # Put in a header line
        first_line = 'Started at: ' + str(datetime.datetime.now()) + '\n'
        self.f_out.write(first_line)
        
        # Run forever, adding one integer at a time from the serial port, 
        #   whenever an integer is available.
        while(1):
            
            my_start_stop_obj.observe()
            
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
                            #sys.stdout.write(' '.join(map(str,currentLinkRSS)) + ' ' + str(timeDiff_ms) + '\n')
                            #sys.stdout.flush()
                            
                            # Write to file
                            self.f_out.write(' '.join(map(str,currentLinkRSS)) + ' ' + str(timeDiff_ms) + '\n')
                            
                            # If the button has been pressed, close the file and
                            # get out of observe.
                            if not self.start_stop_obj.is_listen_state_on():
                                self.f_out.close()
                                return 0
                            
                            # Restart with a new line by resetting currentLinkRSS
                            currentLinkRSS = [127] * numLinks
                        
                        # Store the RSS 
                        currentLinkRSS[i] = self.__hex2signedint(currentLine[rssIndex+txId-1])
        
                # Remove serial data from the buffer.
                currentLine = []
    
################################
# Start of the main function

# Create start-stop object
my_start_stop_obj = start_stop()
my_rss_measurement_obj = rss_measurement(my_start_stop_obj)



# Setup the cleanup procedure
signal.signal(signal.SIGTERM, Exit_gracefully)


# Loop forever
while True:
    
    # Observe the GPIO for button presses
    my_start_stop_obj.observe()
    
    # 
    if my_start_stop_obj.is_listen_state_on():
        my_rss_measurement_obj.observe()
        
        

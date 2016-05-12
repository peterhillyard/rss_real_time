import numpy as np

##############################################
# A class for manipulating lines of RSS from linkAllLinks.py
#
# When using listenAllLinks.py, forward and backward links are all saved
# in the following order: (1,2,ch1), (1,3,ch1), ... (1,N,ch1), (2,1,ch1), 
# (2,3,ch1), ... (N,N-1,ch1), (1,2,ch2), ... , (N,N-1,chC)
# There may be occasions when we want only the forward links or only the 
# backward links instead of all of the links.  The following functions take as 
# input a line of RSS values and returns either the forward or the backward 
# link-channels.  The user can also specify which nodes and channels to include.
class RssEditor:
    # Constructor:
    
    # network - a network object
    
    # cur_line_all - the str that contains the RSS and time for one row
    # cur_time - the current time
    # cur_rss_all - the current rss values from the line
    # most_recent_non_missed_rss_all - saves the most recent non-missed-packet RSS for all links
    # all_nonmiss_flag - a flag that indicates if all links have a non-missed-packet RSS
    
    def __init__(self, my_network):
        self.network = my_network
        
        self.cur_line_all = None
        self.cur_time = None
        self.cur_rss_all = None
        
        self.most_recent_non_missed_rss_all = 127.0*np.ones(self.network.num_links_all)
        self.all_nonmiss_flag = 0
    
    ############
    # Methods - We assume that rss_line is a numpy array
    ############       
    
    # This takes a current line (as a string) from the file and parses it into
    # rss and time
    def observe(self,line):
        self.cur_line_all = line
        lineList         = [float(i) for i in line.split()]
        self.cur_time    = lineList.pop(-1)  # remove last element
        self.cur_rss_all = np.array(lineList) # get all rss values       
    
    # Return to the user the rss values requested
    def get_rss(self):
        return self.cur_rss_all[self.network.master_indexes]
    
    # Return to the user the rss values requested.  If the current measurement
    # is a missed packet, exchange it with the most recent non-missed RSS value
    def get_nonmiss_rss(self):
        nonmiss_idx = self.cur_rss_all != 127.0
        self.most_recent_non_missed_rss_all[nonmiss_idx] = self.cur_rss_all[nonmiss_idx]
        
        if (self.all_nonmiss_flag == 0) & (np.sum(self.most_recent_non_missed_rss_all[self.network.master_indexes] == 127.0) == 0):
            self.all_nonmiss_flag = 1
        
        return self.most_recent_non_missed_rss_all[self.network.master_indexes]
    
    # return a 0 if at least one link still has no RSS value.  Otherwise return a 1
    def is_no_nonmissedpackets(self):
        return self.all_nonmiss_flag       
    
    # Return the current time
    def get_time(self):
        return self.cur_time
        
        
            
        
        
        
        
        
        
        
        
        
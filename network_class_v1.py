import numpy as np

# This class contains all of the parameters for a wireless RF sensor network.
# One common need in testing various systems is eliminating nodes, channels, and
# deciding if forward, backward, or all links should be used.  This class allows
# the user to easily delete nodes and channels and specify the type of links
# desired for testing.  In the end, the user has access to the parameters of the
# original network as well as the modified network.  A master index list is also
# provided so that the user can quickly grab rss values from the original data
# and have it in an order that is easy to process.

# No more need to figure out how to index those many node .txt rss files!

class aNetwork:
    # Constructor: 
    
    # node_locs_all - the node locations for all nodes (before any node elimination)
    # num_nodes_all - number of nodes (before any node elimination)
    # num_ch_all - number of channels (before any channel elimination)
    # num_links_all - number of link tuples (tx,rx,ch) (before any node and channel elimination)
    # num_link_lines_all - number of link lines where there is one link line per node pair (before any node elimination)
    # links_per_link_line_all - number of links per link line (before channel elimination)
    # node_list - list of nodes the user wants to include (node id starts with 1 not 0)
    # ch_list - list of channels the user wants to include (channel id starts with 1 not 0)
    # link_order_choice - forward, backward, forward-backward, or all configurations (f,b,fb,a)
    
    # node_locs_subset - the node locations for the subset of nodes (after node elimination)
    # num_nodes_subset - number of nodes (after node elimination)
    # num_ch_subset - number of channels (after channel elimination)
    # num_links_subset - number of link tuples (tx,rx,ch) (after node and channel elimination)
    # num_link_lines_subset - number of link lines where there is one link line per node pair (after node elimination)
    # links_per_link_line_subset - number of links per link line (after channel elimination and link order choice)
    # link_ch_database: the (id, tx, rx, ch) tuple for each link in the order they are are arranged in listenLinks.py
    # master_indexes - the indexes of the links in the order specified by the user.
    #                  The elements of the vector are the link id for the [(tx,rx,ch)] list of tuples
    #                  The order of the elements determines where the link belongs with respect to the other links
    #                  The elements and the order are determined by the user's node list, channel list, and link order choice                   
    
    
    def __init__(self, node_locs, num_nodes, num_ch, node_list, ch_list, link_order_choice):
        
        self.node_locs_all = node_locs
        self.num_nodes_all = num_nodes
        self.num_ch_all = num_ch
        self.num_links_all = self.num_nodes_all*(self.num_nodes_all-1)*self.num_ch_all
        self.num_link_lines_all = self.num_nodes_all*(self.num_nodes_all-1)/2
        self.links_per_link_line_all = self.num_ch_all*2
        
        self.node_list = node_list
        self.ch_list = ch_list
        self.link_order_choice = link_order_choice
        
        self.node_locs_subset = self.node_locs_all[self.node_list-1,:]
        self.num_nodes_subset = self.node_list.size
        self.num_ch_subset = self.ch_list.size
        self.num_links_subset = None
        self.num_link_lines_subset = self.num_nodes_subset*(self.num_nodes_subset-1)/2
        self.links_per_link_line_subset = None
        self.link_ch_database = None
        
        self.master_indexes = None
        
        self.get_idx()
        
    # Get the indexes corresponding to user specifications
    def get_idx(self):
        
        # create link-channel database
        counter = 0
        link_ch_database = []
        for cc in range(self.num_ch_all):
            for tx in range(self.num_nodes_all):
                for rx in range(self.num_nodes_all):
                    if tx != rx:
                        link_ch_database.append([counter,tx+1,rx+1,cc+1])
                        counter += 1
        link_ch_database = np.array(link_ch_database)
        self.link_ch_database = link_ch_database
        
        # Get indexes of forward and backward links
        fw_idx = link_ch_database[:,1] < link_ch_database[:,2]
        bw_idx = np.logical_not(fw_idx)
        aw_idx = link_ch_database[:,1] > -1.
         
        # Get channel indexes
        ch_idx = np.zeros(self.num_links_all)
        for cc in self.ch_list:
            ch_idx = (ch_idx == 1) | (link_ch_database[:,-1] == (cc))
             
        # Get link indexes
        tx_idx = np.zeros(self.num_links_all)
        rx_idx = np.zeros(self.num_links_all)
        for nn in self.node_list:
            tx_idx += (nn == link_ch_database[:,1])
            rx_idx += (nn == link_ch_database[:,2])
        link_idx = (tx_idx == 1) & (rx_idx == 1)
         
        # create master index array
        master_fw_idx = fw_idx & ch_idx & link_idx
        master_bw_idx = bw_idx & ch_idx & link_idx
        master_aw_idx = aw_idx & ch_idx & link_idx
         
        # Get the index of the backward links
        tmp = np.zeros((link_ch_database.shape[0],3))
        tmp[:,0:2] = link_ch_database[:,1:3]
        tmp[:,-1] = np.arange(link_ch_database.shape[0])
        tmp2 = tmp[master_bw_idx,:]
         
        tmp4 = [[] for cc in range(self.num_ch_subset)]
         
        for nn in self.node_list.tolist():
            tmp3 = tmp2[tmp2[:,1] == nn]
            val = tmp3.shape[0]/self.num_ch_subset
            for cc in range(self.num_ch_subset):
                tmp4[cc] += tmp3[val*cc+np.arange(val),2].tolist()
        
        # get integer indexes of the links
        master_fw_ints = link_ch_database[master_fw_idx,0]
        master_bw_ints = np.array(tmp4).flatten().astype(int)
        master_aw_ints = link_ch_database[master_aw_idx,0]
        
        # set the master integer indexes
        if self.link_order_choice == 'f':
            self.master_indexes = master_fw_ints
            self.links_per_link_line_subset = self.num_ch_subset
        elif self.link_order_choice == 'b':
            self.master_indexes = master_bw_ints
            self.links_per_link_line_subset = self.num_ch_subset
        elif self.link_order_choice == 'fb':
            self.master_indexes = np.array(master_fw_ints.tolist() + master_bw_ints.tolist())
            self.links_per_link_line_subset = self.num_ch_subset*2
        elif self.link_order_choice == 'a':
            self.master_indexes = master_aw_ints
            self.links_per_link_line_subset = self.num_ch_subset*2
        
        # compute the number of links in the new network 
        self.num_links_subset = self.master_indexes.size

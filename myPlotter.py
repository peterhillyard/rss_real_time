# This class handles the real-time plotting of RF link measurements.  The user 
# passes in an rss_editor object and the number of samples they want to display
# in the plot.

# Initial release: 27 Jan 2016

import numpy as np
import matplotlib.pyplot as plt
import circ_buff_class as aCircBuff

class MYPLOTTER:
    
    def __init__(self,rss_editor,num_samples):
        self.is_first_plot = 1
        
        self.num_links_to_plot = rss_editor.network.num_links_subset
        self.num_samples = num_samples
        
        self.circBuff = aCircBuff.myCircBuff(self.num_samples,self.num_links_to_plot)
        
        self.fig = None
        self.ax = None
        self.x_vals = np.arange(self.num_samples)-self.num_samples
    
    # Plots the current image.  This is implemented in a class so that plotting 
    # runs as fast as possible.
    def plot_current_image(self,cur_rss):
        
        # Set up the figure if this is the first time through
        if self.is_first_plot:
            self.fig, self.ax = plt.subplots()
            self.link_plot_lines = []
            
            color_list = ['blue','red','black','green','orange','purple','gray',
                          'lemonchiffon','maroon','pink','coral','saddlebrown','tan','plum','olive']
            
            if len(color_list) < self.num_links_to_plot:
                print "Plotting too many links.  Quitting...\n"
                quit()
            
            # initialize all link line line objects
            for ii in range(self.num_links_to_plot):
                tmp, = self.ax.plot([],[],lw=2, color=color_list[ii])
                self.link_plot_lines.append(tmp)
                
            self.ax.set_xlim(left=self.x_vals[0],right=self.x_vals[-1])
            self.ax.set_ylim(-100,-20)
            self.ax.grid(b=True)
            
            self.fig.canvas.draw()            
            plt.show(block=False)
            self.is_first_plot = 0
        
        ########################
        # Put next RSS into the queue
        ########################
        self.circBuff.add_observation(cur_rss)
        tmp_rss = self.circBuff.get_ordered_buffer()
        tmp_rss[tmp_rss == 127] = np.nan
        
        for ii in range(self.num_links_to_plot):
            self.link_plot_lines[ii].set_data(self.x_vals,tmp_rss[ii,:])
        
        self.ax.draw_artist(self.ax.patch)
        for ii in range(self.num_links_to_plot):
            self.ax.draw_artist(self.link_plot_lines[ii])        
        self.fig.canvas.update()
        self.fig.canvas.flush_events()
        
        
        
        
        
        
        
#An example of a class

import numpy as np
from scipy import stats

#
# Author: Peter Hillyard
#
# Purpose: Allows for a circular buffer to refer to the most recent observations
#     and to iterate through the observations from the newest to the oldest

class myCircBuff:
    
    # Circular Buffer Settings
    # B:        the length of the buffer
    # L:        number of links
    # C:        The matrix that will act as our circular buffer
    # num_obs:  number of observations in the circular buffer
    # open_idx: the index where we can add the next observation
    def __init__(self,buff_len_,num_obs_):
        self.B = buff_len_
        self.L = num_obs_
        self.C = np.nan*np.ones((num_obs_,buff_len_))
        self.num_obs = 0
        self.open_idx = np.zeros((num_obs_,1),dtype=int)
        self.row_idx = np.reshape(np.arange(num_obs_), (-1, 1))
        self.prev_med = np.nan*np.ones(num_obs_)

    # Adds a new observation to the circular buffer
    def add_observation(self,obs_):
        # Overwrite the oldest observation with the current observation
        # Update the index of the open index
        # Increment the number of values in the buffer as needed        
        self.C[self.row_idx,self.open_idx] = np.reshape(obs_,(-1,1))
        self.open_idx = (self.open_idx+1) % self.B
        self.num_obs = np.minimum(self.B,self.num_obs+1)
    
    # Add a subset of the observations according to the mask
    def add_observation_sub(self,obs_,cur_mask):
        
        if self.is_full() == 0:
            print "you cannot use this method until the buffer is full.\nQuitting.\n"
            quit()
        
        tmp_row_idx = self.row_idx[cur_mask==1]
        tmp_open_idx = self.open_idx[cur_mask==1]
        
        self.C[tmp_row_idx,tmp_open_idx] = np.reshape(obs_[cur_mask==1],(-1,1))
        self.open_idx = (self.open_idx+np.reshape(cur_mask,(-1,1))) % self.B
        self.num_obs = np.minimum(self.B,self.num_obs+1)

    # returns the number of observations in the buffer
    def get_num_in_buff(self):
        return self.num_obs
    
    # returns a 1 if the buffer is full, 0 otherwise
    def is_full(self):
        return self.num_obs == self.B
    
    # returns a 1 if all but the first entry is zero; 0 otherwise
    def is_all_but_1st_zero(self):
        return (np.sum(self.C == 0) == (self.B-1)) & (self.C[0,(self.open_idx-1)%self.B] != 0)

    # return a specified column in the circular buffer.  In particular, if the 
    # user uses col = 1, we return the most recently added observation.  
    # col = 2 returns the 2nd newest observation, and so on.
    def get_observation(self,col):

        # if the buffer is full
        if self.num_obs == self.B:
            if self.open_idx - col < 0:
                return self.C[:,self.B + (self.open_idx - col)]
            else:
                return self.C[:,self.open_idx-col]
        # if the buffer is not full
        else:
            return self.C[:,self.open_idx-col]


    def print_buffer(self):
        print "Printing buffer...\n"
        # if the buffer is full
        if self.num_obs == self.B:
            tmp_ptr = 1*self.open_idx-1
            if tmp_ptr == -1:
                tmp_ptr = self.B-1
    
            for ii in range(self.B):
                print self.C[:,tmp_ptr]
                tmp_ptr -= 1
                if tmp_ptr == -1:
                    tmp_ptr = self.B-1

        else:
            tmp_ptr = 1*self.open_idx-1
            for ii in range(self.num_obs):
                print self.C[:,tmp_ptr].T
                tmp_ptr -= 1
        print "done printing...\n"
    
    # return the median of the buffer
    def get_median(self):
        tmp = 1*self.C
        tmp[tmp == 127] = np.nan
        return stats.nanmedian(tmp,axis=1)
    
    # Get the median of the buffer.  If nans appear, use the previous median value.
    def get_no_nan_median(self):
        tmp = 1*self.C
        tmp[tmp == 127] = np.nan
        cur_med = stats.nanmedian(tmp,axis=1)
        
        if np.sum(np.isnan(cur_med)) > 0:
            cur_med_is_not_nan_idx = np.logical_not(np.isnan(cur_med))
            self.prev_med[cur_med_is_not_nan_idx] = cur_med[cur_med_is_not_nan_idx]
        else:
            self.prev_med = cur_med
        
        return 1*self.prev_med
        
    
    # return the variance of the buffer.  This converts 127 values to nans and 
    # we compute the variance excluding the nans
    def get_nanvar(self):
        tmp = 1*self.C
        tmp[tmp == 127] = np.nan
        tmp_var = self.my_nanvar(tmp)
	#tmp_var = np.nanvar(tmp,axis=1)
        tmp_var[np.isnan(tmp_var)] = 0
        return tmp_var
    
    # return the mode of the buffer.
    def get_mode(self):
        vals,counts = stats.stats.mode(self.C,axis=1)
        return vals[0,0]
    
    # return the entire buffer as is
    def get_buffer(self):
        return 1*self.C

    # return the entire buffer in the order they were added
    def get_ordered_buffer(self):
        return 1*(np.append(self.C[:,self.open_idx:],self.C[:,0:self.open_idx],1))
    
    # return the mean of the buffer.  This converts 127 values to nans and we 
    # compute the mean excluding the nans
    def get_mean(self):
        tmp = 1*self.C
        tmp[tmp == 127] = np.NAN

        nrows,ncols = tmp.shape
        tmp_mean = np.nansum(tmp,axis=1)/(ncols - np.sum(np.isnan(tmp),axis=1))

        return tmp_mean
    
    # reset this buffer to have nothing in it
    def reset_buffer(self):
        self.C = np.nan*np.ones((self.L,self.B))
        self.num_obs = 0
        self.open_idx = 0

    # Couldn't load nanvar, so I wrote my own
    def my_nanvar(self,my_mat):
        nrows,ncols = my_mat.shape
        denom = 1.0*(ncols - np.sum(np.isnan(my_mat),axis=1))
        denom[denom == 0] = np.nan
        tmp_mean = np.nansum(my_mat,axis=1)/denom
        tmp_mean_mat = np.tile(tmp_mean,(ncols,1)).T
        tmp_var = np.nansum((my_mat - tmp_mean_mat)**2,axis=1)/denom
        
        return tmp_var
    
    # Compute the product of the elements per row
    def get_per_row_prod(self):
        return np.prod(self.C,axis=1)
    
    # compute the sum of the elements per row
    def get_per_row_sum(self):
        return np.sum(self.C,axis=1)
    
    # compute the nansum of the elements per row
    def get_per_row_nansum(self):
        return np.nansum(self.C,axis=1)
    
    # get the number of non-127 values in each row
    def get_nonnan_row_count(self):
        return np.sum(self.C != 127,axis=1)




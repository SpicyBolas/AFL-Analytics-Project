#################
#PACKAGE IMPORTS#
from copy import deepcopy
import pandas as pd
import numpy as np

##################
#HELPER FUNCTIONS#
def decile_binning(data_in):
    data_out = deepcopy(data_in)
    #Get numerical columns
    #Extract only ther numeric columns
    numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
    num_cols = list(data_out.select_dtypes(include=numerics).columns)
    for col in num_cols:
        try:
            data_out.loc[:,col] = pd.qcut(data_out[col],10,duplicates='drop') 
        except:
            continue
    return data_out



#Produces bin combinations for categorical varaibles
def get_bin_combos_cat(list_in):
        list_out = deepcopy(list_in)
        for idx1 in range(len(list_out)):
            for idx2 in range(idx1+1,len(list_out)):
                common_elem = list(set(list_out[idx1]).intersection(list_out[idx2]))
                if len(common_elem) >= 1:
                    #merge into 1
                    to_merge = list_out[idx1]
                    to_merge+=list_out[idx2]
                    new_elem = list(set(to_merge))
                    #remove idx2 and replace idx1
                    list_out[idx1] = new_elem
                    del list_out[idx2]
                    #Restart merges
                    return get_bin_combos_cat(list_out)
        #Once all merging complete, return the list
        return list_out

#Group bins together for categories with less than 5% volume
def group_lt5_bins(df_agg,merge_bins_in):
    #merge with 1 after or one before if at end of index
    all_bins = df_agg.index.to_list()
    merge_list = []
    for bin_name in merge_bins_in:
        row_num = df_agg.index.get_loc(bin_name)
        if row_num==len(df_agg)-1:
            row_num2 = row_num-1
        else:
            row_num2 = row_num+1
        #Match the names with the bin to merge with
        merge_list.append([all_bins[row_num],all_bins[row_num2]])
    #Combine the merge bins with common values
    merge_list_final = get_bin_combos_cat(merge_list)
    return merge_list_final
    
    
#Aggregates the variable for WoE binning
def woe_agg(data,y_col,variable_col):
    #Get total goods and total bads
    total_goods = sum(data[y_col])
    total_bads = len(data)-total_goods
    agg = data.groupby(variable_col).agg(total=(y_col,'count'),goods=(y_col,'sum'))
    agg['bads'] = agg['total']-agg['goods']
    agg['goods_perc'] = agg['goods']/total_goods
    agg['bads_perc'] = agg['bads']/total_goods
    agg['perc'] = (agg['goods']+agg['bads'])/(total_goods+total_bads)
    agg['WoE'] = agg.apply(lambda x: np.log(x.goods_perc/x.bads_perc),axis=1)
    return agg
    
    
#Function to group numerical bins for 0 goods or bads
#takes the aggregate WoE dataframe and the list with 0 goods or zero bads
def group_zeroGB_bins(df_agg,merge_bins_in):
    row_num = []
    index_list = df_agg.index.to_list()
    for bins in merge_bins_in:
        row = df_agg.index.get_loc(bins)
        row_num.append(row)
    
    #For non adjacent bins, get the following row
    idx = 0
    #Define boundary index start for grouping
    bound_idx = 0
    new_merge_list = []
    for idx in range(len(row_num)):
        #if not the final entry
        if row_num[idx] != len(index_list)-1:
            #if the bins are not sequential then create the new bounds
            if row_num[idx] != row_num[idx+1]-1:
                #Check that it's not the final value
                if row_num[idx] != len(index_list)-1:
                    new_merge_list.append(index_list[bound_idx:row_num[idx]+2])
                    bound_idx = row_num[idx+1]
        else:
            #If is the final entry
            #If bound_idx is the final entry merge into the previous grouping
            if bound_idx != len(index_list)-1:
                new_merge_list[-1].append(index_list[row_num[idx]])
            else:
                #Otherwise group all up to the final
                new_merge_list.append(index_list[bound_idx-1:bound_idx+1])
    return new_merge_list
    
    
#Produce list where each entry is a list of entries to merge    
def get_bin_combos_num(list_in):
        #Takes a 2 dimensional array of intervals, 
        #Each row is to be combined
        list_out = deepcopy(list_in)
        merge_list_final = []
        for list_temp in list_in:
            merge_list_final.append(pd.Interval(left=list_temp[0].left,right=list_temp[-1].right,closed='right'))
        return merge_list_final
            
#Define function to combine categorical bins
def rebin_data_cat(variable,merge_list_in):
    for merges in merge_list_in:
        if variable in merges:
            return '_or_'.join(merges)
        else:
            continue
    return variable

#Define function to combine numeric bins
#merge list is prior to combination
#merge list final is the combined intervals
def rebin_data_num(variable,merge_list_in,merge_list_final_in):
    #Initialise index for the final bin
    idx = 0
    for merges in merge_list_in:
        if variable in merges:
            return merge_list_final_in[idx]
        else:
            idx += 1
            continue
    return variable

####################
#IV SUMMARY FUNCTION
####################

#IV Summary function, produces IVs for each variable and
#modifies the input dataset for combined bins
def IV_summary(data_in,y_col):
    #Initialise an empy dataframe for variable names and IV values
    df_IV = pd.DataFrame({'Variable':[],'IV':[]})
    
    #Make copy to output when modified
    data_out = data_in.copy(deep=True)
    #Extract categorical(binned) variables
    num_cols = data_out.select_dtypes('category').columns.to_list()
    cat_cols = data_out.select_dtypes('object').columns.to_list()
    
    #Get total goods and total bads
    total_goods = sum(data_out[y_col])
    total_bads = len(data_out)-total_goods
    
    #Numerical columns
    for col in num_cols:
        #Aggregate the column and derive required IV information
        agg = woe_agg(data_out,y_col,col)
        #Sort in ascending order of bins
        agg.sort_index()
        #Check if any 0 goods/bads
        #Goods
        if(len(agg[agg['goods']==0])==0):
            merge_list = agg[agg['goods']==0].index.to_list()
            merge_list_final = group_zeroGB_bins(agg,merge_list)
            data_out[col].apply(lambda x: rebin_data_num(x,merge_list,merge_list_final)) 
            #Reaggregate after merge
            agg = woe_agg(data_out,y_col,col)
                                
        #Bads
        if(len(agg[agg['bads']==0])==0):
            merge_list = agg[agg['bads']==0].index.to_list()
            merge_list_final = group_zeroGB_bins(agg,merge_list)
            data_out[col].apply(lambda x: rebin_data_num(x,merge_list,merge_list_final))  
            #Reaggregate after merge
            agg = woe_agg(data_out,y_col,col)
                    
        #Compute the IV
        agg['iv'] = (agg['goods_perc'] - agg['bads_perc'])*agg['WoE']
        IV = sum(agg['iv'])
        #Place the IV into the output dataframe
        df_IV.loc[len(df_IV),:] = [col,IV]
        
    #Categorical columns
    for col in cat_cols:
        #Aggregate the column and derive required IV information
        agg = woe_agg(data_out,y_col,col)
        #Sort on WoE for merging of <5% bins 
        agg = agg.sort_values('WoE')
        #Perform binning for buckets less than 5% volume
        merge_bins = agg[agg['perc']<0.05].index.to_list()
        if len(merge_bins) > 0:
            merge_list_final = group_lt5_bins(agg,merge_bins)
            data_out[col] = data_out[col].apply(lambda x: rebin_data_cat(x,merge_list_final))

        #Check if any 0 goods/bads
        #Goods
        if(len(agg[agg['goods']==0])==0):
           #sort on goods
            agg = agg.sort_values('goods')
            merge_list = agg[agg['goods']==0].index.to_list()
            merge_list_final = group_zeroGB_bins(agg,merge_list)
            data_out[col].apply(lambda x: rebin_data_num(x,merge_list,merge_list_final))  
            #Reaggregate after merge
            agg = woe_agg(data_out,y_col,col)

        #Bads
        if(len(agg[agg['bads']==0])==0):
            agg = agg.sort_values('bads')
            merge_list = agg[agg['bads']==0].index.to_list()
            merge_list_final = group_zeroGB_bins(agg,merge_list)
            data_out[col].apply(lambda x: rebin_data_num(x,merge_list,merge_list_final))  
            #Reaggregate after merge
            agg = woe_agg(data_out,y_col,col)

        #Compute the IV
        agg['iv'] = (agg['goods_perc'] - agg['bads_perc'])*agg['WoE']
        IV = sum(agg['iv'])
        #Place the IV into the output dataframe
        df_IV.loc[len(df_IV),:] = [col,IV]
            
    
    #sort the IV dataframe in descending order
    df_IV = df_IV.sort_values('IV',ascending=False)
    #return the modified data and the IV dataframe
    return df_IV,data_out




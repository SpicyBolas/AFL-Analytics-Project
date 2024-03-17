#Description: Merges the player data into one file, removing duplicate columns
#and renaming to intuitive values

#################
#PACKAGE IMPORTS#
import pandas as pd
import numpy as np
import pathlib
import re

#####
#CODE

#For each data sub folder, iterate through and set 
#all files together into a single dataframe

table_list = ['Key_Stats','General_Play','Defence','Disposals','Marks','Possessions','Scoring','Stoppages']

for table_type in table_list:
    data_folder = pathlib.Path(f"./data")
    data_list_path = list(data_folder.rglob("*.csv"))
    data_list = [re.sub('^.*\\\\','',value.__str__()) for value in data_list_path]
    if f"combined_{table_type}.csv" in data_list:
        print(f"Combined file: {table_type} already exists")
        continue
    
    #Get folder path for specific table type
    folder = pathlib.Path(f"./data/{table_type}")
    #Get file list of csv's
    file_list_path = list(folder.rglob("*.csv"))
    #Remove directories prior to the file
    #by replaceing anything prior to '\\'
    #with empty string
    file_list = [re.sub('^.*\\\\','',value.__str__()) for value in file_list_path]

    #Load the first data frame which will be concatenated
    #Remove first two columns (RANK and old Index) since no longer relevant
    df_main = pd.read_csv(f"./data/{table_type}/"+file_list[0]).iloc[:,2:]
    df_main.columns = [col.strip() for col in df_main.columns]
    #Set the data together
    for file in file_list[1:]:
        #Load in next file
        df_temp = pd.read_csv(f"./data/{table_type}/"+file).iloc[:,2:]
        df_temp.columns = [col.strip() for col in df_temp.columns]
        #Concatenate together
        df_main = pd.concat([df_main, df_temp], ignore_index=True)

    #Save down the overall table in data folder
    df_main.to_csv(f"./data/combined_{table_type}.csv")

#Delete no longer needed dataframes
del df_main
del df_temp
############################################ 
#Joining the Player Data for Unique Features
#Extract list of combined data csv files from the data folder
folder = pathlib.Path(f"./data") 
file_list_path = list(folder.rglob("combined*.csv")) 
file_list = [re.sub('^.*\\\\','',value.__str__()) for value in file_list_path]

#Define function to determine common columns
def common_member(df1, df2):
    df1_set = set(df1.columns)
    df2_set = set(df2.columns)
 
    if (df1_set & df2_set):
        #Create a list for all columns except for join conditions
        #of 'Player', 'Season', 'Round'
        common_cols = list(df1_set&df2_set - {'Player','Season','Round'})    
    else:
        common_cols = []
    return common_cols

#Load the first data frame which will be joined
df_main = pd.read_csv(f"./data/"+file_list[0],index_col=0)

#Join data one after the other until all data is present in one table for players
for file in file_list[1:]:
        #Load in next file
        df_temp = pd.read_csv(f"./data/"+file,index_col=0)
        #Obtain common columns prior to join
        common_cols = common_member(df_main,df_temp)
        #Remove the column columns from the second dataframe
        if len(common_cols) > 0:
             df_temp = df_temp.drop(common_cols, axis=1)
        
        #Join together
        df_main = df_main.merge(df_temp, on=['Player','Season','Round'], how='left')

#TODO: Rename the columns to something more intuitive (from the AFL website)
#TODO: Join on the player's team at the time
#TODO: Save down the dataframe in the data folder
#TODO: Delete the raw data no longer needed 

     



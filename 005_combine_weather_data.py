#Description: Combines weather data into a single csv file

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

table_list = ['Adelaide','Alice Springs','Ballarat','Brisbane','Canberra',
              'Darwin','Geelong','Gold Coast','Hobart','Launceston','Melbourne',
             'Perth','Sydney']

for table_type in table_list:
    data_folder = pathlib.Path(f"./data/WeatherData")
    data_list_path = list(data_folder.rglob("*.csv"))
    data_list = [re.sub('^.*\\\\','',value.__str__()) for value in data_list_path]
    if f"combined_{table_type}.csv" in data_list:
        print(f"Combined file: {table_type} already exists")
        continue
    
    #Get folder path for specific table type
    folder = pathlib.Path(f"./data/WeatherData/{table_type}")
    #Get file list of csv's
    file_list_path = list(folder.rglob("*.csv"))
    #Remove directories prior to the file
    #by replacing anything prior to '\\'
    #with empty string
    file_list = [re.sub('^.*\\\\','',value.__str__()) for value in file_list_path]

    #Load the first data frame which will be concatenated
    df_main = pd.read_csv(f'./data/WeatherData/{table_type}/'+file_list[0],encoding='unicode_escape',header=10)
    df_main = df_main.iloc[:,[1,3,5,6,7,8,9,10]]
    df_main.columns = ['Date','Rain (mm)','Max Temp (C)','Min Temp (C)','Max Humid (%)',
                   'Min Humid (%)','Wind Speed (m/s)','Solar Rad (MJ/sq m)']
    #Set the City
    df_main['City'] = table_type
    #Remove final row which is an aggregate
    df_main.drop(index=len(df_main)-1,inplace=True)
    
    #Set the data together
    for file in file_list[1:]:
        #Load in next file
        df_temp = pd.read_csv(f'./data/WeatherData/{table_type}/'+file,encoding='unicode_escape',header=10)
        df_temp = df_temp.iloc[:,[1,3,5,6,7,8,9,10]]
        df_temp.columns = ['Date','Rain (mm)','Max Temp (C)','Min Temp (C)','Max Humid (%)',
                   'Min Humid (%)','Wind Speed (m/s)','Solar Rad (MJ/sq m)']
        #Set the City
        df_temp['City'] = table_type
        #Remove final row which is an aggregate
        df_temp.drop(index=len(df_temp)-1,inplace=True)

        #Concatenate together
        df_main = pd.concat([df_main, df_temp], ignore_index=True)

    #Save down the overall table in data folder
    df_main.to_csv(f"./data/WeatherData/combined_{table_type}.csv")
    #Delete no longer needed dataframes
    del df_main
    del df_temp

#Combine the weather data into a single csv file
#Get folder path for specific table type
folder = pathlib.Path(f"./data/WeatherData")
#Get file list of csv's
file_list_path = list(folder.rglob("combined*.csv"))
#Remove directories prior to the file
#by replacing anything prior to '\\'
#with empty string
file_list = [re.sub('^.*\\\\','',value.__str__()) for value in file_list_path]
 #Load the first data frame which will be concatenated
df_main = pd.read_csv(f'./data/WeatherData/'+file_list[0],index_col=0)

for file in file_list[1:]:
        #Load in next file
        df_temp = pd.read_csv(f'./data/WeatherData/'+file,index_col=0)
        #Concatenate together
        df_main = pd.concat([df_main, df_temp], ignore_index=True)

#Save down the overall table in data folder
df_main.to_csv(f"./data/WeatherData_v1.csv")

#Clean up, deleting combined files
for file_name in file_list_path:
     pathlib.Path(file_name).unlink()
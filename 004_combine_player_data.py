#Description: Merges the player data into one file, removing duplicate columns
#and renaming to intuitive values

#################
#PACKAGE IMPORTS#
import pandas as pd
import numpy as np
import pathlib
import re
from thefuzz import fuzz

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

#Create copy as the raw player dataset
df_main_raw = df_main.copy(deep=True)
#Load in player team data
df_main['lPlayer'] = df_main['Player'].str.lower()
df_team_player = pd.read_csv('./data/player_team.csv',index_col=0)
df_team_player['lPlayer'] = df_team_player['Player'].str.lower()

###############
#FUZZY MATCHING 
#Remaining unmatched names try find a closest match (fuzzy matching)#
df_outer =df_main.merge(df_team_player,on=['Season','lPlayer'],how='outer') 

mismatch_names_x = df_outer[df_outer['Player_y'].isna()].loc[:,['Player_x']].sort_values('Player_x').drop_duplicates()
mismatch_names_x['join_idx'] = 1

mismatch_names_y = df_outer[df_outer['Player_x'].isna()].loc[:,['Player_y']].sort_values('Player_y').drop_duplicates()
mismatch_names_y['join_idx'] = 1

#Full join the two name dataframes
df_joined = mismatch_names_x.merge(mismatch_names_y,on='join_idx',how='left')

#Get the simlarity ratio between the two
df_joined['Similarity'] = df_joined.apply(lambda x: fuzz.ratio(x.Player_x,x.Player_y),axis=1)

#Sort in descending order of similarity by Player_x
df_matched = df_joined.sort_values(['Player_x','Similarity'],ascending=[True,False]).drop_duplicates(['Player_x'])
#Remove those with similarity score 74 or less
df_matched = df_matched[df_matched['Similarity']>74].loc[:,['Player_x','Player_y']]


####################
#JOINING PREPARATION
#Remove Callum Brown to manually correct later
df_matched=df_matched[df_matched['Player_y'] != 'Callum Brown']
#Get the unmatched names from the team dataframe
#First get the macthed names as a list
df_matched_y = df_matched['Player_y'].to_list()

#Loop through and replace names for joining purposes
for name in df_matched_y:
    replacement = df_matched.loc[df_matched['Player_y']==name,'Player_x'].values[0]
    df_team_player.loc[df_team_player['Player']==name,'Player'] = replacement
    df_main.loc[df_main['Player']==name,'Player'] = replacement

##AD HOC PLAYER CHANGES
#Replace 'Angus Dewy' with 'Angus Litherland'
df_team_player.loc[df_team_player['Player']=='Angus Dewar','Player'] = 'Angus Litherland'
df_main.loc[df_main['Player']=='Angus Dewar','Player'] = 'Angus Litherland'
#Change Ian Hill name
df_main.loc[df_main['Player']=='Ian Hill','Player'] = 'Bobby Hill'

#Recreate lower case player version for joining
df_team_player.drop('lPlayer',axis=1)
df_team_player['lPlayer'] = df_team_player['Player'].str.lower()
df_main.drop('lPlayer',axis=1)
df_main['lPlayer'] = df_main['Player'].str.lower()

#############
#Join team onto table by Season and player name
df_main = df_main.merge(df_team_player.drop('Player',axis=1),on=['Season','lPlayer'],how='left')
#Note: 2643 rows are not joined on successfully, investigate differences in
print('There are: ',sum(df_main['Team'].isna()),' empty Team cells')

#############################################
#MANUAL FIXES TO REMAINING UNIDENTIFIED TEAMS
#Matching team's were found through AFL website or otherwise
df_main.loc[df_main['Player']=='Abe Davis','Team'] = 'Sydney'
df_main.loc[df_main['Player']=='Callum M. Brown','Team'] = 'Greater Western Sydney'
df_main.loc[df_main['Player']=='Callum L. Brown','Team'] = 'Collingwood' #Correction, had previously been left out
df_main.loc[df_main['Player']=='Clay Cameron','Team'] = 'Gold Coast'
df_main.loc[df_main['Player']=='Daniel Pearce','Team'] = 'Western Bulldogs'
df_main.loc[df_main['Player']=='Fraser McInnes','Team'] = 'West Coast'
df_main.loc[(df_main['Player']=='Jason Ashby')&(df_main['Season']==2013),'Team'] = 'Essendon'
df_main.loc[(df_main['Player']=='Jeremy Taylor')&(df_main['Season']==2013),'Team'] = 'Gold Coast'
df_main.loc[(df_main['Player']=='Jordan Gysberts')&(df_main['Season']==2013),'Team'] = 'North Melbourne'
df_main.loc[df_main['Player']=='Jordan Kelly','Team'] = 'Hawthorn'
df_main.loc[df_main['Player']=='Josh P. Kennedy','Team'] = 'Sydney'
df_main.loc[(df_main['Player']=='Lewis Stevenson')&(df_main['Season']==2012),'Team'] = 'Port Adelaide'
df_main.loc[(df_main['Player']=='Shane Kersten')&(df_main['Season']==2013),'Team'] = 'Geelong'
df_main.loc[(df_main['Player']=='Todd Banfield')&(df_main['Season']==2013),'Team'] = 'Brisbane Lions'

##############################################################
#CORRECTION FOR NAMES AND TEAMS FOR PLAYERS WITH SIMILAR NAMES
#Rename 'Player' column for later joining
df_main_raw = df_main_raw.rename(columns={'Player':'Player_corr'})
#Get columns to join together raw and processed data
join_cols = df_main_raw.columns.to_list()
join_cols.remove('Player_corr')

#Join the raw player name onto the main data
df_join = df_main.merge(df_main_raw,on=join_cols,how='left')

#Extract Bobby Hill and Angus Litherland data to prevent removal in fuzzy matching
bobbyHillRounds = ['Round '+ str(i) for i in range(17,24)]
bobbyHillRounds.append('Preliminary Finals')
df_bobbyHill = df_main[(df_main['Player']=='Bobby Hill')&(df_main['Season']==2019)&(df_main['Round'].isin(bobbyHillRounds))]
df_angusLitherland = df_main[(df_main['Player']=='Angus Litherland')&(df_main['Season']==2022)&(df_main['Round']=='Round 2')]
#Keep data rows to place back into the dataset
df_to_concat = pd.concat([df_bobbyHill,df_angusLitherland],ignore_index=True)

#Create name similarity score between the old and new data playerr names
df_join['Name_Sim_Score'] = df_join.apply(lambda x: fuzz.ratio(x.Player,x.Player_corr),axis=1)

#If in the similar names list replace 'Player' with 'Player_corr',
#otherwise leave the same
corr_names_list = ['Scott D. Thompson','Sam J. Reid','Josh J. Kennedy',
    'Tom J. Lynch','Mitchell Brown','Bailey J. Williams']

#Function for name replacement
def correct_names(x):
    if x.Player in corr_names_list:
        return x.Player_corr
    else:
        return x.Player

#Keep only those with 80 or higher sim score to filter out
#duplicate rows created by the same player stats in a given round
#(rare occurrence but does happen)
df_temp = df_join.loc[df_join['Name_Sim_Score']>=80,:]
#Correct the names
df_temp.loc[:,'Player'] = df_temp.apply(correct_names,axis=1)
 #Discard the Player_corr and similarity score columns, no longer needed
df_temp.drop(['Player_corr','Name_Sim_Score'],inplace=True,axis=1)
#Add back in Bobby Hill and Angus Litherland data
df_corrected = pd.concat([df_temp,df_to_concat],ignore_index=True)
#Remove any duplicate rows
df_corrected.drop_duplicates(inplace=True)

#Reassign Team for the similar names
#Scott D. Thompson
df_corrected.loc[df_corrected['Player']=='Scott D. Thompson','Team'] = 'North Melbourne'
#Scott Thompson
df_corrected.loc[df_corrected['Player']=='Scott Thompson','Team'] = 'Adelaide'

#Sam J. Reid
df_corrected.loc[df_corrected['Player']=='Sam J. Reid','Team'] = 'Greater Western Sydney'
#Sam Reid
df_corrected.loc[df_corrected['Player']=='Sam Reid','Team'] = 'Sydney'

#Josh P. Kennedy
df_corrected.loc[df_corrected['Player']=='Josh P. Kennedy','Team'] = 'Sydney'
#Josh J. Kennedy
df_corrected.loc[df_corrected['Player']=='Josh J. Kennedy','Team'] = 'West Coast'

#Tom J. Lynch
df_corrected.loc[(df_corrected['Player']=='Tom J. Lynch')&(df_corrected['Season']<=2018),'Team'] = 'Gold Coast'
df_corrected.loc[(df_corrected['Player']=='Tom J. Lynch')&(df_corrected['Season']>2018),'Team'] = 'Richmond'
#Tom Lynch
df_corrected.loc[df_corrected['Player']=='Tom Lynch','Team'] = 'Adelaide'

#Mitch Brown: West Coast
df_corrected.loc[df_corrected['Player']=='Mitch Brown','Team'] = 'West Coast'
#Mitchell Brown
df_corrected.loc[(df_corrected['Player']=='Mitchell Brown')&(df_corrected['Season']<=2014),'Team'] = 'Geelong'
df_corrected.loc[(df_corrected['Player']=='Mitchell Brown')&(df_corrected['Season']>2014)&(df_corrected['Season']<=2019),'Team'] = 'Essendon'
df_corrected.loc[(df_corrected['Player']=='Mitchell Brown')&(df_corrected['Season']>2019),'Team'] = 'Melbourne'

#Bailey J. Williams
df_corrected.loc[df_corrected['Player']=='Bailey J. Williams','Team'] = 'West Coast'
#Bailey Williams
df_corrected.loc[df_corrected['Player']=='Bailey Williams','Team'] = 'Western Bulldogs'

#Remove duplicate rows
df_corrected.drop_duplicates(inplace=True)

#Save down the Player Data
df_corrected.to_csv('./data/PlayerData_v1.csv')


     



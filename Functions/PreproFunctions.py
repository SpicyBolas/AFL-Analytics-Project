#################
#PACKAGE IMPORTS#
import pandas as pd
import numpy as np
import re
from datetime import datetime
from sklearn.model_selection import train_test_split

#Function to create non encoded TOP DOWN dataset
def top_down_preproc(data_players_in,data_match_in,max_date):
    #Make copies of the input data frames for processing 
    data_players = data_players_in.copy(deep=True)
    data_matches = data_match_in.copy(deep=True)
    #################
    #Players Dataset#
    #Remove the 'lPlayer' column, City and any rows with ToG% == 0 and prior to selected data
    data_players.drop('lPlayer',axis=1,inplace=True)
    data_players = data_players[(data_players['ToG%']>0)&(data_players['Season']<max_date)]
    #Remove plural 's' from 'Round' Column for later joining
    data_players.loc[:,'Round'] = data_players['Round'].str.replace(r's$','',regex=True)
    ###############
    #Match Dataset#
    #Remove 'City'
    data_matches.drop('City',axis=1,inplace=True)
    #Rename 'H/A' and H/A_opp' for ease of string use
    data_matches['HA'] = data_matches['H/A']
    data_matches.drop('H/A',axis=1,inplace=True)

    data_matches['oppHA'] = data_matches['oppH/A']
    data_matches.drop('oppH/A',axis=1,inplace=True)
    #Covert weather data into floats
    weather_cols = ['Max Temp (C)','Min Temp (C)','Max Humid (%)','Min Humid (%)','Wind Speed (m/s)',\
                    'Solar Rad (MJ/sq m)','Rain (mm)']
    data_matches[weather_cols] = data_matches[weather_cols].apply(pd.to_numeric,errors='coerce')
    #Keep only pre max_date
    data_matches = data_matches[data_matches['Season']<max_date] 
    #Commonise the 'Round' Column
    data_matches.loc[(data_matches['Round']=='Qualifying Final')|(data_matches['Round']=='Elimination Final'),'Round'] = 'Finals Week 1'
    ########
    #Joining
    #Aggregate the player data to join to the match data
    #Extract only ther numeric columns
    numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
    num_cols = list(data_players.select_dtypes(include=numerics).columns)
    #Append Round and Team
    num_cols.append('Round')
    num_cols.append('Team')
    #Keep only numeric and aggregation variables
    data_play_num = data_players[num_cols]
    #Take sum of Shots-At-Goal (SAG), ScoreLaunches (SL), Goals (G), behinds (B) and mean otherwise
    data_play_num1 = data_play_num[['Season','Round','Team','SAG','SL','G','B']]
    data_play_num2 = data_play_num.drop(['SAG','SL','G','B'],axis=1)
    #Aggregate by Season, Round and Team
    df_play_agg = data_play_num1.groupby(['Season','Round','Team']).agg('sum').reset_index()
    df_play_agg2 = data_play_num2.groupby(['Season','Round','Team']).agg('mean').reset_index()
    #Join together
    df_play_agg = df_play_agg.merge(df_play_agg2,on=['Season','Round','Team'],how='left')

    #Join on team data
    df_matches_v2 = data_matches.merge(df_play_agg,on=['Season','Round','Team'],how='left')
    #Join on opponent data
    df_matches_v2 = df_matches_v2.merge(df_play_agg,left_on=['Season','Round','Opponent'],right_on=['Season','Round','Team'],\
                                    how='left',suffixes=('_team','_opp'))
    #Rename Team_team to Team and drop Team_opp
    df_matches_v2.rename(columns={'Team_team':'Team'},inplace=True)
    df_matches_v2.drop('Team_opp',axis=1,inplace=True)

    #Rename Round for ease of sorting
    round_dict = {'Finals Week 1':25,'Semi Final':26,'Preliminary Final':27,\
                'Grand Final':28}
    #Define function to change values based on dict
    def rename_round(x):
        if x in list(round_dict.keys()):
            return round_dict[x]
        else:
            return int(re.search(r'(\d+)',x)[0])
        
    #Apply changes to round names
    df_matches_v2['RoundNum'] = df_matches_v2['Round'].apply(rename_round)
    
    #Sort entries to appear in chronological order
    df_matches_v2 = df_matches_v2.sort_values(['Team','Season','RoundNum'])
    
    ######################
    #HANDLE MISSING VALUES
    #Fill na with 0 for Rain (mm) and Attendance
    df_matches_v2.loc[:,['Rain (mm)','Attendance']] = df_matches_v2[['Rain (mm)','Attendance']].fillna(0.0)
    #Fill remaining with means
    impute_cols = ['Max Temp (C)','Min Temp (C)','Max Humid (%)','Min Humid (%)','Wind Speed (m/s)','Solar Rad (MJ/sq m)']
    df_matches_v2.loc[:,impute_cols] = df_matches_v2[impute_cols].fillna(df_matches_v2[impute_cols].mean()) 

    ###################################
    #HISTORICAL FEATURES FOR PREDICTION
    #Extract necessary columns for lagging
    df_team_stats = df_matches_v2.filter(regex=(".+_opp|.+_team"))
    df_team_stats = pd.concat([df_team_stats,df_matches_v2[['Attendance','PointsF','PointsA']]],axis=1)
    #Remove these columns from the match dataframe
    df_matches_v2 = df_matches_v2.drop(df_team_stats.columns.to_list(),axis=1)
    #Average the last 5 matches in the season as predictors
    df_team_stats = df_team_stats.rolling(5,closed='left').mean()
    #Join back on to the match dataframe
    df_matches_v2 = pd.concat([df_matches_v2,df_team_stats],axis=1)
    
    ####################
    #FEATURE ENGINEERING

    ##Last Winner of the current match up##
    #Create columns to designate the number in which this match up has appeared
    df_matches_v2['MatchUpNum'] = df_matches_v2.groupby(['Team','Opponent']).cumcount()
    df_matches_v2['MatchUpP1'] = df_matches_v2['MatchUpNum']+1
    #Self join to get the previous winner of the current match up
    df_matches_v2 = df_matches_v2.merge(df_matches_v2[['Team','Opponent','MatchUpP1','Outcome']],left_on=['Team','Opponent','MatchUpNum'],
                   right_on=['Team','Opponent','MatchUpP1'],how='left')
    #Remove no longer needed variables
    df_matches_v2 = df_matches_v2.drop(['MatchUpNum','MatchUpP1_x','MatchUpP1_y'],axis=1)
    #Rename columns altered by join
    df_matches_v2 = df_matches_v2.rename(columns={'Outcome_x':'Outcome','Outcome_y':'Last_Winner'})

    ##Running % Season Wins##
    #Get the cumulative number of wins for the season for each team
    df_matches_v2['cum_wins'] = df_matches_v2[['Team','Season','Outcome']].groupby(['Team','Season'])['Outcome'].cumsum()
    #Get running total number of matches per season per team
    df_matches_v2['cum_count'] = df_matches_v2[['Team','Season','Outcome']].groupby(['Team','Season']).cumcount()+1
    #Derive running win % and lag by 1
    df_matches_v2['season_win_rate'] = (df_matches_v2['cum_wins']/df_matches_v2['cum_count']).shift()
    #Remove the variables used in derivation
    df_matches_v2 = df_matches_v2.drop(['cum_wins','cum_count'],axis=1)
    
    ##Max Humidity Rename##
    df_matches_v2['Max_Humid'] = df_matches_v2['Max Humid (%)']

    #Solar Radiation Rename
    df_matches_v2['Solar_Rad'] = df_matches_v2['Solar Rad (MJ/sq m)']
    df_matches_v2 = df_matches_v2.drop('Solar Rad (MJ/sq m)',axis=1)

    #HTW% Rename
    df_matches_v2['HTW_perc_team'] = df_matches_v2['HTW%_team']
    df_matches_v2 = df_matches_v2.drop('HTW%_team',axis=1)
    df_matches_v2['HTW_perc_opp'] = df_matches_v2['HTW%_opp']
    df_matches_v2 = df_matches_v2.drop('HTW%_opp',axis=1)

    #HTW% Rename
    df_matches_v2['CDL_perc_team'] = df_matches_v2['CDL%_team']
    df_matches_v2 = df_matches_v2.drop('CDL%_team',axis=1)
    df_matches_v2['CDL_perc_opp'] = df_matches_v2['CDL%_opp']
    df_matches_v2 = df_matches_v2.drop('CDL%_opp',axis=1)


    ##Max season Win streak##
    #create lagged Team and Season
    df_matches_v2['Team_lag'] = df_matches_v2['Team'].shift()
    df_matches_v2['Season_lag'] = df_matches_v2['Season'].shift()
    #create function to produce win streak
    df_matches_v2['win_streak'] = 0
    for i in range(len(df_matches_v2)):
        if pd.isna(df_matches_v2.iloc[i,:]['Team_lag'])\
        or pd.isna(df_matches_v2.iloc[i,:]['Season_lag'])\
        or (df_matches_v2.iloc[i,:]['Season'] != df_matches_v2.iloc[i,:]['Season_lag'])\
        or (df_matches_v2.iloc[i,:]['Team'] != df_matches_v2.iloc[i,:]['Team_lag']):
            df_matches_v2.iloc[i, df_matches_v2.columns.get_loc('win_streak')] = df_matches_v2.iloc[i,:]['Outcome']
        else:
            if df_matches_v2.iloc[i,:]['Outcome'] == 1:
                df_matches_v2.iloc[i, df_matches_v2.columns.get_loc('win_streak')] = df_matches_v2.iloc[i-1,:]['win_streak'] + df_matches_v2.iloc[i,:]['Outcome']
            else:
                df_matches_v2.iloc[i, df_matches_v2.columns.get_loc('win_streak')] = 0
    #Lag the win streak by 1
    df_matches_v2['win_streak'] = df_matches_v2['win_streak'].shift()
    #Remove the variables used in derivation
    df_matches_v2 = df_matches_v2.drop(['Team_lag','Season_lag'],axis=1)
    
    ##Days since last match##
    df_matches_v2['Date'].apply(lambda x: datetime.strptime(x,'%d-%b-%Y'))
    df_matches_v2['Date_lag'] = df_matches_v2['Date'].shift().bfill()
    df_matches_v2['days_last_match'] = (df_matches_v2['Date'].apply(lambda x: datetime.strptime(x,'%d-%b-%Y')) -\
        df_matches_v2['Date_lag'].apply(lambda x: datetime.strptime(x,'%d-%b-%Y'))).dt.days
    #Remove the variables used in derivation
    df_matches_v2 = df_matches_v2.drop('Date_lag',axis=1)

    #Remove Round 1-5 to remove NAN values
    df_matches_v3 = df_matches_v2[~((df_matches_v2['Round'].isin(['Round 1','Round 2','Round 3','Round 4','Round 5'])))]

    #Remove rows still containing NaN in 'Last_Winner'
    df_matches_v3 = df_matches_v3.dropna()
    return df_matches_v3

#Encode and split the data for training
def encode_split_data(data_in,OOT_year,encode=False):
    #Remover the time based data and points for and against at present match
    #Remove Season later after separating into IT/OOT
    df_ML = data_in.drop(['Round','Date','RoundNum'],axis=1)

    #Encode the categorical variables
    #Identify and remove the object data and convert to category
    if encode:
        df_categories = df_ML.select_dtypes(include=['object']).astype('category')
        cat_cols = df_categories.columns
        #Remove from the ML data to join back on later
        df_ML.drop(cat_cols,axis=1,inplace=True)
        #One Hot Encode the categories
        df_categories = pd.get_dummies(df_categories,dtype=int)
        #Join back on to the df_ML data
        df_ML = df_ML.join(df_categories)
    
    #Define function for splitting
    def split_preprocess(data):
        data_IT = data[data['Season']<OOT_year]
        data_OOT = data[data['Season']>=OOT_year] 
        #Get the dependent variable
        y = data_IT.pop('Outcome')
        #Split the in time data, stratify by outcome and shuffle
        X_train, X_test, y_train, y_test = train_test_split(data_IT,y,test_size=0.3,shuffle=True,random_state=5432,stratify=y)
        #Return the split data
        return data_IT, data_OOT, X_train, X_test, y_train, y_test

    #Split the data
    df_ML_IT, df_ML_OOT, X_train, X_test, y_train, y_test = split_preprocess(df_ML)
    #Drop season from all the data
    X_train.drop('Season',axis=1,inplace=True)
    X_test.drop('Season',axis=1,inplace=True)

    return df_ML_IT,df_ML_OOT,X_train,y_train,X_test,y_test









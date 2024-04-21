#Description: Makes predictions for the week's data
#TODO: Remove hard coding of the round and season selected
#TODO: Update to new model using last season finalist variables
#################
#PACKAGE IMPORTS#
from bs4 import BeautifulSoup 
import requests
import pandas as pd
import numpy as np
import re

#####
#Code

#AFL Table
#load in the tables through years 2012 to 2024 taking teams,
#points, venue, attendance, date, Season, Round

#Create empty data frame to insert values into
df_matches = pd.DataFrame({'Team1':[],'Team2':[],'Points1':[],'Points2':[],'G_team1':[],'G_team2':[],'AttenTime':[],
                                 'Venue':[],'Season':[],'Round':[]})
#Create list of years to iterate through
#Obtain team data for all years
years = 2024

#Loop through seasons and insert data into the data frame
document = requests.get(f'https://afltables.com/afl/seas/{years}.html')
soup = BeautifulSoup(document.text,features='html.parser')

tables = soup.find_all('table')
#Initialise Round Number
round_num = None
for table in tables:
    #Update the round number
    if len(table.find_all('tr')) == 1:
        round_temp = table.find('tr').find('td').text.strip()
        if round_temp != 'Finals':
            round_num = round_temp
    elif len(table.find_all('tr')) == 2:
        rows = table.find_all('tr')
        #Extract the matches
        #Get attendance and match date
        atd_time_info = rows[0].find_all('td')[3].text.strip()

        #Get first team and venue
        links = rows[0].find_all('a')
        venue = links[1].text.strip()
        team1 = links[0].text.strip()
        team1_score = rows[0].find_all('td')[2].text.strip()
        team1_goals = re.sub('^([^\d]+)','',rows[0].find_all('td')[1].text.strip().split(' ')[-1].split('.')[0])
        #Get second team
        links = rows[1].find_all('a')
        team2 = links[0].text.strip()
        team2_score = rows[1].find_all('td')[2].text.strip()
        team2_goals = re.sub('^([^\d]+)','',rows[1].find_all('td')[1].text.strip().split(' ')[-1].split('.')[0])
        #Insert data into the table
        df_matches.loc[len(df_matches),:] = [team1,team2,team1_score,team2_score,team1_goals,team2_goals,
                                                atd_time_info,venue,years,round_num]

#Extract the date and attendance from the AttenTime column
df_matches["DateTime"] = df_matches["AttenTime"].str.extract(r'^([a-zA-Z]{3}\s\d{2}-[a-zA-Z]{3}-\d{4})') 
df_matches['Day'] = df_matches["DateTime"].str.extract(r'(^[a-zA-Z]{3})')
df_matches['Date']= df_matches["DateTime"].str.extract(r'(\d{2}-[a-zA-Z]{3}-\d{4})')

df_matches['Attendance'] = df_matches["AttenTime"].str.extract(r'Att:\s([\d,]+)')
df_matches['Attendance'] = df_matches['Attendance'].replace('',np.NaN)
df_matches['Attendance'] = df_matches['Attendance'].str.replace(r'[^\d]','',regex=True).apply(float)

#Convert values to integer format
df_matches['Season'] = df_matches['Season'].apply(int)
df_matches['Points1'] = df_matches['Points1'].replace('',np.NaN)
df_matches['Points1'] = df_matches['Points1'].astype(float)
df_matches['Points2'] = df_matches['Points2'].replace('',np.NaN)
df_matches['Points2'] = df_matches['Points2'].astype(float)

#Drop the temporary columns
df_matches.drop(['AttenTime','DateTime'],axis=1,inplace=True)

#Define Team 1 Winner Flag
df_matches['Winner1'] = df_matches.apply(lambda x: int(x.Points1>x.Points2),axis=1)
df_matches.loc[df_matches['Points1'].isna(),['Winner1']] = pd.NA

#Save down the data as a csv
#df_matches.to_csv('./data/MatchData_v1.csv')

##########################
#Get home/away information
#From wikipedia get home teams for different stadiums
document = requests.get('https://en.wikipedia.org/wiki/List_of_Australian_Football_League_grounds')
soup = BeautifulSoup(document.text,features='html.parser')

#Extract the tables
tables = soup.find_all('table')
table_current = tables[0]
table_former = tables[1]

#Convert tables into dataframes
#########################
#Extract the column names
#Current
header_current = table_current.find('tr').find_all('th')
columns_current = []
for col in header_current:
    columns_current.append(col.text.strip())
    
#Remove the image column
del columns_current[1] 
#Former
header_former = table_former.find('tr').find_all('th')
columns_former = []
for col in header_former:
    columns_former.append(col.text.strip())

#Create dataframes
df_current = pd.DataFrame(columns=columns_current)
df_former = pd.DataFrame(columns=columns_former)

#Loop through and insert data into each dataframe
#Current
rows = table_current.find_all('tr')[1:]
for row in rows:
    #Get all data in row
    datas = row.find_all('td')
    #initialise empty list for row to insert
    row_to_insert = []
    #Create the row to insert
    #Counter to determine if first column
    counter = 0
    for data in datas:
        if counter == 0:
            row_to_insert.append(data.find('a').get('title').strip())
        else:
            row_to_insert.append(data.text.strip())
        counter += 1 #increment the counter
    idx = len(df_current)
    #Insert the data at present row
    df_current.loc[idx,:] = row_to_insert
    
#Former
rows = table_former.find_all('tr')[1:]
for row in rows:
    #Get all data in row
    datas = row.find_all('td')
    #initialise empty list for row to insert
    row_to_insert = []
    #Create the row to insert
    for data in datas:
        row_to_insert.append(data.text.strip())
    idx = len(df_former)
    #Insert the data at present row
    df_former.loc[idx,:] = row_to_insert

###################
#Process df_current
#Extract only needed columns and add a Last used column
#Add placeholder date of 9999 for last used if still current
df_current = df_current.loc[:,['Ground','First used','Current tenant(s)']]
df_current['Last used'] = 9999
#Convert 'First used' into integer
df_current['First used'] = df_current['First used'].str.replace(r'\[.+\]','',regex=True).apply(int)
#Separate out the tennants into their own columns
#Remove square bracket artefacts
df_current['Current tenant(s)'] = df_current['Current tenant(s)'].str.replace(r'\[.+\]','',regex=True)
#Separate team names by a hyphen
df_current['Current tenant(s)'] = df_current['Current tenant(s)'].str.replace(r'([a-z])([A-Z])',r'\1-\2',regex=True)
df_teams_temp = df_current['Current tenant(s)'].str.split('-',expand=True)
#Join on the Ground column as the id var
df_loc_teams = df_current.loc[:,['Ground']].join(df_teams_temp)
#Melt the dataframe
df_loc_teams = df_loc_teams.melt(id_vars=['Ground'],var_name='team_idx',value_name='Team').drop('team_idx',axis=1)
#Remove any rows with Team as None
df_loc_teams = df_loc_teams.dropna()
#Join back on to original table for many-to-one relationship
df_current = df_current.drop(['Current tenant(s)'],axis=1).merge(df_loc_teams,on='Ground',how='left')

#Rename grounds names for joining and consistency with match data
df_current.loc[df_current['Ground']=='Carrara Stadium',['Ground']] = 'Carrara'
df_current.loc[df_current['Ground']=='Docklands Stadium',['Ground']] = 'Docklands'
df_current.loc[df_current['Ground']=='The Gabba',['Ground']] = 'Gabba'
df_current.loc[df_current['Ground']=='Melbourne Cricket Ground',['Ground']] = 'M.C.G.'
df_current.loc[df_current['Ground']=='Sydney Cricket Ground',['Ground']] = 'S.C.G.'
df_current.loc[df_current['Ground']=='Sydney Showground Stadium',['Ground']] = 'Sydney Showground'

##################
#Process df_former
#Only index of 5,12,13 are in relevent date range 
df_former = df_former.loc[[5,12,13],['Ground','First used','Last used','Tenant(s)']]
#Rename Columns
df_former.columns = ['Ground','First used','Last used','Current tenant(s)']

#Convert 'First used' and 'Last used' into integer
df_former['First used'] = df_former['First used'].str.replace(r'\[.+\]','',regex=True).apply(int)
df_former['Last used'] = df_former['Last used'].str.replace(r'\[.+\]','',regex=True).apply(int)
#Clean Strings for 'Current tenant(s)
df_former['Current tenant(s)'] = df_former['Current tenant(s)'].str.replace(r'\[.+\]','',regex=True)
#Separate out the tennants into their own columns
#Remove square bracket artefacts
df_former['Current tenant(s)'] = df_former['Current tenant(s)'].str.replace(r'\[.+\]','',regex=True)
#Separate team names by a hyphen
df_former['Current tenant(s)'] = df_former['Current tenant(s)'].str.replace(r'^([a-zA-Z\s]+):[^a-zA-Z]+([a-zA-Z\s]+):[^a-zA-Z]+',r'\1-\2',regex=True)
#Perform operation on lower case then capital for 'Football Park' 
df_former.loc[df_former['Ground']=='Football Park','Current tenant(s)'] = df_former.loc[df_former['Ground']=='Football Park','Current tenant(s)'].str.replace(r'([a-z])([A-Z])',r'\1-\2',regex=True)
df_teams_temp = df_former['Current tenant(s)'].str.split('-',expand=True)
#Join on the Ground column as the id var
df_loc_teams = df_former.loc[:,['Ground']].join(df_teams_temp)
#Melt the dataframe
df_loc_teams = df_loc_teams.melt(id_vars=['Ground'],var_name='team_idx',value_name='Team').drop('team_idx',axis=1)
#Remove any rows with Team as None
df_loc_teams = df_loc_teams.dropna()

#Join back on to original table for many-to-one relationship
df_former = df_former.drop(['Current tenant(s)'],axis=1).merge(df_loc_teams,on='Ground',how='left')
#Rename for consistency
df_former.loc[df_former['Ground']=='Subiaco Oval',['Ground']] = 'Subiaco'

######################################
#COMBINING CURRENT AND FORMER STADIUMS
#Concatenate the current and previous dataframes together
df_venues = pd.concat([df_current,df_former],axis=0,ignore_index=True)
#Rename Ground to Venue
df_venues.columns = ['Venue','First used','Last used','Team']
#No longer need 'First used' or 'Last used'
df_venues = df_venues.drop(['First used','Last used'],axis=1)
#Change 'Brisbane' to 'Brisbane Lions' for joining
df_venues.loc[df_venues['Team']=='Brisbane','Team'] = 'Brisbane Lions'
#Create a flag used to determine if home game:
df_venues['Home/Away'] = 'H'

###############################################
#Join Home/Away Variable onto the match dataset
#Home/Away for Team 1
#Join on by team name, Venue and date to determine Home/Away for each team
df_matches_temp = df_matches.merge(df_venues,left_on=['Venue','Team1'],right_on=['Venue','Team'],how='left')
#Remove ther extra 'Team' column
df_matches_temp = df_matches_temp.drop('Team',axis=1)
#Fill NA home and Away values with 'A' for away
df_matches_temp['Home/Away'] = df_matches_temp['Home/Away'].fillna('A')
#Rename 'Home/Away' for Team 1
df_matches_temp.rename(columns={'Home/Away':'Home/Away1'}, inplace=True)
#Reassign to df_matches
df_matches = df_matches_temp.copy(deep=True)

#Home/Away for Team 2
#Join on by team name, Venue and date to determine Home/Away for each team
df_matches_temp = df_matches.merge(df_venues,left_on=['Venue','Team2'],right_on=['Venue','Team'],how='left')
#Remove ther extra 'Team' column
df_matches_temp = df_matches_temp.drop('Team',axis=1)
#Fill NA home and Away values with 'A' for away
df_matches_temp['Home/Away'] = df_matches_temp['Home/Away'].fillna('A')
#Rename 'Home/Away' for Team 2
df_matches_temp.rename(columns={'Home/Away':'Home/Away2'}, inplace=True)
#Reassign to df_matches
df_matches = df_matches_temp.copy(deep=True)

##########################
#Produce two-sided dataset

#Modify dataset to contain both sides of the matches as rows
#Rename columns in preparation for creating a combined dataset 
df_matches = df_matches.rename({'Team1':'Team','Team2':'Opponent','Points1':'PointsF',
                    'Points2':'PointsA','G_team1':'G_team','G_team2':'G_opp','Winner1':'Outcome',
                   'Home/Away1':'H/A','Home/Away2':'oppH/A'}, axis='columns')

#Create a copy of the dataset and rename columns to have opponent side
df_matches_opp = df_matches.copy(deep=True)
#Rename columns for other side of match
df_matches_opp = df_matches_opp.rename({'Team':'Opponent','Opponent':'Team','PointsF':'PointsA',
                    'PointsA':'PointsF','G_team':'G_opp','G_opp':'G_team',
                   'H/A':'oppH/A','oppH/A':'H/A'}, axis='columns')
#Redefine Outcome for opponent side
df_matches_opp['Outcome'] = abs(df_matches_opp['Outcome']-1) 

#Concatenate the two sides of the matches
df_matches_out = pd.concat([df_matches,df_matches_opp],ignore_index=True)


##############################
#Make Predictions for the Week
#Load in old match data from prior years
df_matches_v2 = pd.read_csv('./data/MatchData_v2.csv',index_col=0)

#Combine the old and new data for feature derivation
df_matches_comb = pd.concat([df_matches_out,df_matches_v2[df_matches_v2['Season']<=2023]],axis=0)


#Feature Engineering: Last Winner:
#Redefine round names
df_matches_comb.loc[(df_matches_comb['Round']=='Qualifying Final')|(df_matches_comb['Round']=='Elimination Final'),'Round'] = 'Finals Week 1'
##Last Winner of the current match up##
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
df_matches_comb['RoundNum'] = df_matches_comb['Round'].apply(rename_round)

#Sort entries to appear in chronological order
df_matches_comb = df_matches_comb.sort_values(['Team','Season','RoundNum'])

#Create columns to designate the number in which this match up has appeared
df_matches_comb['MatchUpNum'] = df_matches_comb.groupby(['Team','Opponent']).cumcount()
df_matches_comb['MatchUpP1'] = df_matches_comb['MatchUpNum']+1
#Self join to get the previous winner of the current match up
df_matches_comb = df_matches_comb.merge(df_matches_comb[['Team','Opponent','MatchUpP1','Outcome']],left_on=['Team','Opponent','MatchUpNum'],
               right_on=['Team','Opponent','MatchUpP1'],how='left')
#Remove no longer needed variables
df_matches_comb = df_matches_comb.drop(['MatchUpNum','MatchUpP1_x','MatchUpP1_y'],axis=1)
#Rename columns altered by join
df_matches_comb = df_matches_comb.rename(columns={'Outcome_x':'Outcome','Outcome_y':'Last_Winner'})
#Take only the latest season matches
df_matches_comb_v2 = df_matches_comb[df_matches_comb['Season']>=years]

########################
#Derive Season Win Rate:
df_matches_comb_v2['cum_wins'] = df_matches_comb_v2[['Team','Season','Outcome']].groupby(['Team','Season'])['Outcome'].cumsum()
#Get running total number of matches per season per team
df_matches_comb_v2['cum_count'] = df_matches_comb_v2[['Team','Season','Outcome']].groupby(['Team','Season']).cumcount()+1
#Derive running win % and lag by 1
df_matches_comb_v2['season_win_rate'] = (df_matches_comb_v2['cum_wins']/df_matches_comb_v2['cum_count']).shift()
#Remove the variables used in derivation
df_matches_comb_v2 = df_matches_comb_v2.drop(['cum_wins','cum_count'],axis=1)
df_matches_comb_v3 = df_matches_comb_v2[['Team','Opponent','Season','Round','H/A','G_team','G_opp','oppH/A','Outcome','Last_Winner','season_win_rate']]

#Self Join to get opposition season win rate
df_matches_comb_v3 = df_matches_comb_v3.merge(df_matches_comb_v3[['Opponent','Season','Round','season_win_rate']],left_on=['Team','Season','Round']
                         ,right_on=['Opponent','Season','Round'],how='left')

#Remove the Opponent_y column
df_matches_comb_v3.drop('Opponent_y',axis=1,inplace=True)
#Rename columns as required
df_matches_comb_v3 = df_matches_comb_v3.rename(columns={'Opponent_x':'Opponent','season_win_rate_x':'season_win_rate_team','season_win_rate_y':'season_win_rate_opp'})

df_matches_comb_v3['G_team'] = pd.to_numeric(df_matches_comb_v3['G_team'],errors='coerce')

#Get the rolling average number of goals per team
df_matches_comb_v3['G_team_roll'] = df_matches_comb_v3[['Team','G_team']].groupby('Team').rolling(5,min_periods=1).mean().shift().reset_index()['G_team']

#Self Join to get opposition season win rate
df_matches_comb_v3 = df_matches_comb_v3.merge(df_matches_comb_v3[['Opponent','Season','Round','G_team_roll']],left_on=['Team','Season','Round']
                         ,right_on=['Opponent','Season','Round'],how='left')

df_matches_comb_v3.drop(['Opponent_y','G_team_roll_x'],axis=1,inplace=True)

df_matches_comb_v3 = df_matches_comb_v3.rename(columns={'Opponent_x':'Opponent','G_team_roll_y':'G_opp_final'})

#Rename to the HA column for consistency
df_matches_comb_v3 = df_matches_comb_v3.rename(columns = {'H/A':'HA','oppH/A':'oppHA'})

############################
#MODEL APPLICATION FUNCTION#
def apply_model(x):
    #intercept
    logit = 0.9503
    #Team HA
    if x.HA == 'H':
        logit += 0.3557
    #Opponent HA    
    if x.oppHA == 'H':
        logit += -0.3049
    
    #G_opp
    if pd.isna(x.G_opp_final): 
        logit += 0 
    else:
        logit += x.G_opp_final*-0.0775
    
    #Season win rate team
    if pd.isna(x.season_win_rate_team):
        logit += 0
    else:
        logit += 2.3101*x.season_win_rate_team
        
    #Season win rate opp
    if pd.isna(x.season_win_rate_opp):
        logit += 0
    else:
        logit += -2.7537*x.season_win_rate_opp
    
    #Last Winner:
    if pd.isna(x.Last_Winner):
        logit += 0
    else:
        logit += x.Last_Winner*0.3777
        
    #Define logit to prob function 
    def logit_to_prob(logit):
        return 1/(1+np.exp(-logit))
    
    return logit_to_prob(logit)
        
#Apply the model
df_matches_comb_v3['Prob'] = df_matches_comb_v3.apply(apply_model,axis=1)        

#Join on the opposite probability and take the average
df_matches_comb_v3 = df_matches_comb_v3.merge(df_matches_comb_v3[['Opponent','Season','Round','Prob']],left_on=['Team','Season','Round'],
                                                                                           right_on=['Opponent','Season','Round'],how='left')

df_matches_comb_v3.drop(['Opponent_y'],axis=1,inplace=True)

df_matches_comb_v3 = df_matches_comb_v3.rename(columns={'Opponent_x':'Opponent','Prob_x':'Prob_team','Prob_y':'Prob_opp'})

df_matches_comb_v3['Prob_final_team'] = (df_matches_comb_v3['Prob_team']+(1-df_matches_comb_v3['Prob_opp']))/2     

#Get only relevant matches:
#Extract Rows for upcoming matches
df_matches_comb_v3['Outcome_lag'] = df_matches_comb_v3['Outcome'].shift()

#Filter to only take latest unpredicted round
df_final = df_matches_comb_v3[(df_matches_comb_v3['Round']=='Round 7')][['Team','Opponent','Season','Round','Prob_final_team']]

#Create unique index for deduplicating the two match sides
def team_opp_col(x):
    out_list = [x.Team,x.Opponent]
    out_list.sort()
    return tuple(out_list)

df_final['Team_opp'] = df_final.apply(team_opp_col,axis=1)

#Final dataframe for outputting
df_out = df_final.drop_duplicates('Team_opp').drop('Team_opp',axis=1)


#########################
#Save down the data as a csv
df_out.to_csv(f'./data/Weeks_Predictions.csv')



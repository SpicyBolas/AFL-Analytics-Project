#Description: Extracts and saves match data by year (2012-2024) from AFL Table website
#################
#PACKAGE IMPORTS#
from bs4 import BeautifulSoup 
import requests
import pandas as pd
import numpy as np

#####
#Code

#AFL Table
#load in the tables through years 2012 to 2024 taking teams,
#points, venue, attendance, date, Season, Round

#Create empty data frame to insert values into
df_matches = pd.DataFrame({'Team1':[],'Team2':[],'Points1':[],'Points2':[],'AttenTime':[],
                                 'Venue':[],'Season':[],'Round':[]})
#Create list of years to iterate through
#Obtain team data for all years
years = list(range(2012,2025))

#Loop through seasons and insert data into the data frame
for year in years:
    document = requests.get(f'https://afltables.com/afl/seas/{year}.html')
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
            #Get second team
            links = rows[1].find_all('a')
            team2 = links[0].text.strip()
            team2_score = rows[1].find_all('td')[2].text.strip()

            #Insert data into the table
            df_matches.loc[len(df_matches),:] = [team1,team2,team1_score,team2_score,
                                                 atd_time_info,venue,year,round_num]

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

#########################
#Save down the data as a csv
df_matches.to_csv('./data/MatchData_v1.csv')

#TODO: Join on player injuries

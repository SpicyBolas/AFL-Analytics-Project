#Description: Extracts and saves player teams by year (2012-2024) from AFL Table website
#################
#PACKAGE IMPORTS#
from bs4 import BeautifulSoup 
import requests
import pandas as pd
import re
import time

#####
#Code

#load in the tables through years 2012 to 2024 taking team
#and player names, assigning year column

#Create empty data frame to insert values into
df_teams_players = pd.DataFrame({'Season':[],'Team':[],'Player Raw':[]})
#Create list of years to iterate through
#Obtain team data for all years
years = list(range(2012,2025))
for year in years:
    document = requests.get(f'https://afltables.com/afl/stats/{year}.html')

    soup = BeautifulSoup(document.text,features='html.parser')
    #Take only team related tables (ignoring the first)
    tables = soup.find_all('table')[1:]

    for table in tables:
        #Extract Team
        team = table.find('a').text
        #Extract useful rows (ingoring the header row)
        table_row = table.find_all('tr')[1:]
        #Loop through and obtain player names
        for row in table_row:
            data_coll = row.find_all('a')
            if len(data_coll) == 0:
                continue

            for data in row.find_all('a'):
                player = data.text
            #Insert into the dataframe
            idx = len(df_teams_players)
            df_teams_players.loc[idx,:] = [year,team,player]


#Correct the Player name formatting
#Function arranges as {first_name} {last_name}
def arrange_name(string):
    p = re.compile(r'(.[^,]+),\s(.+)')
    return p.sub(r'\2 \1',string)


#Apply function to the data frame
df_teams_players['Player'] = df_teams_players['Player Raw'].apply(arrange_name)

#Add apostrophes to last names in from "{letter}{captial Letter}"
def irish_name_fix(string):
    return re.sub(r'([A-Z])([A-Z])',r"\1'\2",string)
#Add apostrophe to Irish names
df_teams_players['Player'] = df_teams_players['Player'].apply(irish_name_fix)

#Convert Season to integer
df_teams_players['Season'] = df_teams_players['Season'].apply(int)

#Remove the raw player name
df_teams_players.drop('Player Raw',axis=1,inplace=True)
#Save as csv
df_teams_players.to_csv('./data/player_team.csv')
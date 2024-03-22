#Description: Extracts and saves player teams by year (2012-2024) from AFL Table website
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

#Save down the data as a csv
df_matches.to_csv('./data/MatchData_v1.csv')


#TODO: Join on Home or Away Team from wikipedia Stadium Info
#TODO: Join on Weather forecasts/occurrences
#TODO: Join on player injuries

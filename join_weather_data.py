#Description: Creates new match data after joining on the weather for the area and day

#################
#PACKAGE IMPORTS#
import pandas as pd
import numpy as np

#####
#CODE

#Load in weather and match data
df_weather = pd.read_csv('./data/WeatherData_v1.csv',index_col=0)
df_matches = pd.read_csv('./data/MatchData_v1.csv',index_col=0)

#Change Date format for join
df_weather['Date'] = pd.to_datetime(df_weather['Date'],format='%d/%m/%Y')
df_weather['Date'] = df_weather['Date'].dt.strftime('%d-%b-%Y')

#Create a dictionary mapping Venues to Cities
city_dict = {'Stadium Australia':'Sydney','M.C.G.':'Melbourne','Carrara':'Gold Coast','Subiaco':'Perth',
            'Docklands':'Melbourne','Football Park':'Adelaide','Gabba':'Brisbane','S.C.G.':'Sydney',
            'Bellerive Oval':'Hobart','Blacktown':'Sydney','Kardinia Park':'Geelong','Manuka Oval':'Canberra',
            'York Park':'Launceston','Marrara Oval':'Darwin','Sydney Showground':'Sydney','Adelaide Oval':'Adelaide',
            'Traeger Park':'Alice Springs','Eureka Stadium':'Ballarat','Perth Stadium':'Perth','Norwood Oval':'Adelaide'}

#Function to create city column
def venue_to_city(x):
    if x in list(city_dict.keys()):
        return city_dict[x]
    else:
        return ''

#Map the venues to cities
df_matches['City'] = df_matches['Venue'].apply(venue_to_city)

#Join thwe weather data to the match data
df_matches = df_matches.merge(df_weather,on=['Date','City'],how='left')

#Save down the newly created match data
df_matches.to_csv('./data/MatchData_v2.csv')
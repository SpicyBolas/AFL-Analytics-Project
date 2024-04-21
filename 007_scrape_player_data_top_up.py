#Description: Tops up and saves player data (2024) from AFL website
#################
#PACKAGE IMPORTS#
from bs4 import BeautifulSoup 
import requests
import pandas as pd  
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import re
import time
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
#options.add_argument('--headless') #Make visible so dynamic loading works
options.add_argument('--start-maximized')

#########################
#Variables and Constants#
category = 'Key+Stats'
seasonId = 2
roundId = 5
roundNumber = 1
sortColumn = 'dreamTeamPoints'

CategoryList = list(range(8))
SeasonList = 0
RoundCodes = 'r6'
###########################
#MAIN CODE#

#define Selenium attributes for finding elements
ID ="id"
CLASS_NAME = "class name"

#####################################
#CREATE WEB DRIVER and EXTRACT TABLE#
driver = webdriver.Chrome(options)
driver.get(f'https://www.afl.com.au/stats/leaders?\
                category={category}&seasonId={seasonId}&roundId={roundId}&roundNumber={roundNumber}\
                &sortColumn={sortColumn}&sortDirection=descending&\
                positions=All&teams=All&benchmarking=falsee&dataType=totals&playerOneId=null&playerTwoId=null')


round_code = RoundCodes
#Condition which will be broken once round no longer exists
#Select Season
#Activate dropdown
element = driver.find_elements(By.CSS_SELECTOR,"div.stats-leaders-nav__item-wrapper")[1]
ac = ActionChains(driver)
ac.move_to_element(element).move_by_offset(0, 0).click().perform()
#Wait 2 seconds
time.sleep(2)
#Select 
season_elem = driver.find_element(By.ID,f'downshift-:r4:-item-{SeasonList}')
ac.move_to_element(season_elem).move_by_offset(0, 0).click().perform()

#Select the round
#Initialise round at 1
round_iter = 2

while True:
    #Click the round drop down
    element = driver.find_elements(By.CSS_SELECTOR,"div.stats-leaders-nav__item-wrapper")[2]
    ac = ActionChains(driver)
    ac.move_to_element(element).move_by_offset(0, 0).click().perform()
    #Wait 2 seconds
    time.sleep(2)
    #Check if round exists, break the loop if it doesn't 
    try:
        round_elem = driver.find_element(By.ID,f'downshift-:{round_code}:-item-{round_iter}')
        round_iter += 1
    except:
        print('No Round')
        print(round_code)
        round_elem = False
        break

    ac.move_to_element(round_elem).move_by_offset(0, 0).click().perform()

    #Select the Category
    element = driver.find_elements(By.CSS_SELECTOR,"div.stats-leaders-nav__item-wrapper")[0]
    ac = ActionChains(driver)
    ac.move_to_element(element).move_by_offset(0, 0).click().perform()
    #Wait 2 seconds
    time.sleep(2)
    #Select Category, initialise at Key Stats
    category_elem = driver.find_element(By.ID,'downshift-:r0:-item-0')
    ac.move_to_element(category_elem).move_by_offset(0, 0).click().perform()
    #Wait 2 seconds
    time.sleep(2)        
    #Check if data exists, break the loop if it doesn't 
    try:
        table_elem = driver.find_element(By.CLASS_NAME,'stats-table')
    except:
        print('No Stats Table')
        #Set round_iter such that the next season is analysed
        round_iter = 'None'
        break
    #Wait 2 seconds
    time.sleep(2)
    #Obtain the "show more button" 
    try:
        show_more = driver.find_element(By.CLASS_NAME,"stats-table-load-more-button")
    except:
        show_more=False

    #Keep clicking the button until it no longer exists
    while(show_more):
        #Click show more
        show_more.click()
        #Try find the element, set to False if does not exist
        try:
            show_more = driver.find_element(By.CLASS_NAME,"stats-table-load-more-button")
        except:
            show_more = False

    for category_iter in CategoryList: 
        #Change categories if 2nd or higher run
        if category_iter > 0:
            #Select the Category
            element = driver.find_elements(By.CSS_SELECTOR,"div.stats-leaders-nav__item-wrapper")[0]
            ac = ActionChains(driver)
            ac.move_to_element(element).move_by_offset(0, 0).click().perform()
            #Wait 2 seconds
            time.sleep(0.5)
            #Select Category, initialise at Key Stats
            category_elem = driver.find_element(By.ID,f'downshift-:r0:-item-{category_iter}')
            ac.move_to_element(category_elem).move_by_offset(0, 0).click().perform()
            #Wait 2 seconds
            time.sleep(0.5)
        
        soup = BeautifulSoup(driver.page_source,features='html.parser')
        #Look for second table if available otherwise take table 1
        try:
            table = soup.find_all('table')[1]
        except:
            table = soup.find_all('table')[0]
        #Create table headers
        colnames = []
        #get table header
        headers = table.find('tr').find_all('th')

        for header in headers: 
            colnames.append(header.text)
            
        #Append column for season
        colnames.append('Season')
        #Append column for round
        colnames.append('Round')

        #Create key_stats dataframe
        df_stats = pd.DataFrame(columns=colnames)
        #Insert additional column heading for position
        df_stats.insert(2,"Position",[])

        #Get the Season and Round from the page
        nav_bar_info = soup.find('div',{'class': 'stats-leaders-nav'})
        stat_info = nav_bar_info.find_all('span',{'class':'select__current-text'})
        #Create a list of the selector headings
        stat_list = []
        for stat in stat_info:
            stat_list.append(stat.text)
        #Get only unique values
        stat_list = list(dict.fromkeys(stat_list))
        print(stat_list)
        #Assign the values of category type, season and round
        category_type = stat_list[0]
        season = stat_list[1]
        round_number = stat_list[2]
        #extract only number from season for file naming
        season_num = re.sub(r'[^0-9]','',season)


        #get table rows
        table_rows = table.find_all('tr')[1:]
        for row in table_rows:
            row_to_insert = []
            
            position = row.find_all('span',{"class": "stats-leaders-table-position-badge"})[0].text
            
            data = row.find_all('td')
            #Set up counter to determine when to extract player name
            counter = 0
            for entry in data:
                if counter == 1:
                    player_str = entry.find('button')['title']
                    player = re.sub(r':.+','',player_str)
                    row_to_insert.append(player)
                    row_to_insert.append(position)
                #Increment counter after each loop
                counter += 1
                #Append text data to list
                row_to_insert.append(entry.text)
            #append season
            row_to_insert.append(season_num)
            #append round
            row_to_insert.append(round_number)
            
            idx = len(df_stats)
            df_stats.loc[idx,:] = row_to_insert

        #Replace whitespace with underscore for depositing file
        category_dir = re.sub(r'\s','_',category_type)
        #Save down csv file in data location
        df_stats.to_csv(f'./data/{category_dir}/{season_num}_{round_number}_{category_type}.csv')

        #Delete the data frame
        del df_stats
        
driver.quit()



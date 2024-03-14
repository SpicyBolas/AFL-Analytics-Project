#Description: Extracts and saves player data (2012-2024) from AFL website
#################
#PACKAGE IMPORTS#
from bs4 import BeautifulSoup 
import requests
import pandas as pd  
from selenium import webdriver
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
options.add_argument('--ignore-ssl-errors')
options.add_argument('--headless')
#TODO: Silence the console logs/errors 

#########################
#Variables and Constants#
seasonIdList = ['2','4','5','7','9','11','14','18','20','34','43','52','62']

###########################
#TEST SPACE for Extraction#

category = 'Key+Stats'
seasonId = '11'
roundId = '149'
roundNumber = '1'
sortColumn = 'dreamTeamPoints'

#####################################
#CREATE WEB DRIVER and EXTRACT TABLE#

driver = webdriver.Chrome(options)
driver.get(f'https://www.afl.com.au/stats/leaders?\
                    category={category}&seasonId={seasonId}&roundId={roundId}&roundNumber={roundNumber}\
                    &sortColumn={sortColumn}&sortDirection=descending&\
                    positions=All&teams=All&benchmarking=true&dataType=benchmarkedTotals&playerOneId=null&playerTwoId=null')

soup = BeautifulSoup(driver.page_source,features='html.parser')
driver.quit()
table = soup.find('table')

#Print table headers
for header in table.find('tr').find_all('th'): 
    print(header.text)
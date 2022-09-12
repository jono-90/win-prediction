import subprocess
import re
from webbrowser import get
import requests
import urllib3
import time
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import os

class Champion:
  def __init__(self, name, winrate):
    self.name = name
    self.winrate = winrate
    self.id = 0

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

def compare_current_champs(champions):
        # Batch command to get the client process
        command = "WMIC PROCESS WHERE name='LeagueClientUx.exe' GET commandline"

        # Execute the command
        output = subprocess.Popen(command, stdout=subprocess.PIPE,
                                shell=True).stdout.read().decode('utf-8')

        # Extract needed args
        port = re.findall(r'"--app-port=(.*?)"', output)[0]
        password = re.findall(r'"--remoting-auth-token=(.*?)"', output)[0]

        # Disable the annoying certificate error
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Set up session
        session = requests.session()
        session.verify = False

        myTeam = []
        theirTeam = []

    # Running in an infinite loop, so the user doesn't have to restart the script all the time
        while True:
            
            req = session.get('https://127.0.0.1:%s/lol-champ-select/v1/session' % port, auth=requests.auth.HTTPBasicAuth('riot', password))

            if req.status_code == 200:

                results = json.loads(req.text)

                tmp_myTeam = []
                for c in results['myTeam']:
                    tmp_myTeam.append(c['championId'])
                tmp_myTeam.sort()

                tmp_theirTeam = []
                for c in results['theirTeam']:
                    tmp_theirTeam.append(c['championId'])
                tmp_theirTeam.sort()
                
                if (myTeam != tmp_myTeam):
                    myTeam = tmp_myTeam
                
                if (theirTeam != tmp_theirTeam):
                    theirTeam = tmp_theirTeam

            # Override with some dummy data
            #myTeam = [22,143,82,201,711]
            #theirTeam = [122,154,13,51,267]

            #winrate logic
            if (len(myTeam) == 5 and len(theirTeam) == 5):
                print('Calculating win rate')

                mywinrate = 0.0
                theirwinrate = 0.0

                for m in myTeam:
                    for w in win_rates:
                        if m == w.id:
                            mywinrate = mywinrate + w.winrate
                            print(w.name + ': ' + str(w.winrate))
                            continue
                
                for t in theirTeam:
                    for w in win_rates:
                        if t == w.id:
                            theirwinrate = theirwinrate + w.winrate
                            print(w.name + ': ' + str(w.winrate))
                            continue                            

                mywinrate = mywinrate / 5
                theirwinrate = theirwinrate / 5
                print ('My Teams Win Rate: ' + str(mywinrate))
                print ('Their Teams Win Rate: ' + str(theirwinrate))
            else:
                print('full team not available yet, please wait...')
                print(myTeam)
                print(theirTeam)

            time.sleep(5)

def get_lolalytics() -> BeautifulSoup:

    # Check if we have already scraped lolalytics today and return the html.
    todaysscrape = datetime.today().strftime('%Y-%m-%d') + '.html'
    if (todaysscrape in os.listdir()):
        with open(todaysscrape, 'r') as f:
            contents = f.read()
        return BeautifulSoup(contents, "html.parser")


    # If we get this far, we need to scrape a new html file.
    options = Options()
    options.headless = True
    options.add_argument("--window-size=1920,1200")

    url = 'https://lolalytics.com/lol/tierlist/'

    DRIVER_PATH = 'C:\\Users\\jono-\\Downloads\\chromedriver_win32\\chromedriver'
    driver = webdriver.Chrome(options=options, executable_path=DRIVER_PATH)
    driver.get(url)

    try:
        element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ListRow_rank__2A39S"))
        )
    except:
        print("something went wrong, could not find champion list")

    source = driver.page_source
    driver.close()

    file = open(todaysscrape, 'w')
    file.write(source)
    file.close()

    with open(todaysscrape, 'r') as f:
        contents = f.read()
    return BeautifulSoup(contents, "html.parser")

def get_win_rates(soup):

    champions = []

    champion_div = soup.find('div', class_='TierList_list__j33gd') #get champ table
    children = champion_div.findChildren(recursive=False) # get table rows
    
    for child in children:
        namecol = child.find('div', class_='ListRow_name__b5btO') # get name column
        name = namecol.findChildren('a', recursive=False)[0].text # extract champ name

        wrcol = child.findChildren(recursive=False)[5] # get winrate column
        winrate = float(wrcol.findChildren(recursive=False)[0].text)
        
        champions.append(Champion(name, winrate))

    return champions

def build_champion_dictionary(win_rates):
    
    url = 'http://ddragon.leagueoflegends.com/cdn/12.16.1/data/en_US/champion.json'
    session = requests.session()
    session.verify = False
    req = session.get(url).json()

    champdict = {}

    for c in req['data'].values():
        champdict.update({c['name']:c['key']})

    # Weird bug - naming convention differences for my boy Nunu
    champdict.update({'Nunu':'20'})
    
    for w in win_rates:
        w.id = int(champdict[w.name])

    return win_rates

if __name__ == '__main__':
    try:        

        soup = get_lolalytics() # get lolalytics data 
        win_rates = get_win_rates(soup) # extract win rates
        champions = build_champion_dictionary(win_rates) # add champ id's with data dragon info

        compare_current_champs(champions)

    except KeyboardInterrupt:
        exit()
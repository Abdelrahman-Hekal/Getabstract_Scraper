
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
import pandas as pd
import time
import csv
import sys
import numpy as np

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_page_load_timeout(60)
    driver.maximize_window()

    return driver

def scrape_getabstract(path, login_username, login_pass):

    start = time.time()
    print('-'*75)
    print('Scraping getabstract.com ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'getabstract_data.xlsx'
        # getting the books under each category
        links = []
        nbooks = 0
        url = 'https://www.getabstract.com/en/explore?page=682&sorting=bestselling&audioFormFilter=false&languageFormFilter=en&sourceFormFilter=BOOK&minRatingFormFilter=5&minPublicationDateFormFilter=0'
        driver.get(url)
        # scraping books urls
        titles = wait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.summary-card")))
        for title in titles:
            try:
                nbooks += 1
                print(f'Scraping the url for book {nbooks}')
                link = wait(title, 5).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                links.append(link)
            except Exception as err:
                print('The below error occurred during the scraping from getabstract.com, retrying ..')
                print('-'*50)
                print(err)
                continue

        # saving the links to a csv file
        print('-'*75)
        print('Exporting links to a csv file ....')
        with open('getabstract_links.csv', 'w', newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Link'])
            for row in links:
                writer.writerow([row])

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        name = path.split('\\')[-1][:-4]
        name = name + '_data.xlsx'
    else:
        df_links = pd.read_csv('getabstract_links.csv')

    links = df_links['Link'].values.tolist()

    try:
        data = pd.read_excel(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass

    # scraping books details
    print('-'*75)
    print('Logging In...')
    print('-'*75) 
    if login_username == '' or login_pass == '':
        print('Invalid credentials for logging in, press any key to exit...')
        input()
        sys.exit()
    try:
        driver.get('https://www.getabstract.com/en/login')
        user = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//input[@name='username']")))
        password = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//input[@name='password']")))
        user.send_keys(login_username)
        time.sleep(2)
        password.send_keys(login_pass)
        time.sleep(2)
        button = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//button[@class='btn btn-primary']")))
        driver.execute_script("arguments[0].click();", button)
        time.sleep(5)
    except:
        print('Failed to login, press any key to exit...')
        input()
        sys.exit()

    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        try:
            if link in scraped: continue
            driver.get(link)           
            details = {}
            print(f'Scraping the info for book {i+1}\{n}')

            # title and title link
            title_link, title = '', ''
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).get_attribute('textContent').replace('\n', '').strip().title() 
            except:
                print(f'Warning: failed to scrape the title for book: {link}')            
                
            details['Title'] = title
            details['Title Link'] = title_link               
            
            # subtitle
            subtitle = ''
            try:
                subtitle = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h2.lead.sumpage-header__subtitle"))).get_attribute('textContent').replace('\n', '').strip() 
            except:
                try:
                    subtitle = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h2.h5.sumpage-review-header__subtitle"))).get_attribute('textContent').replace('\n', '').strip() 
                except:
                    pass          
                
            details['Subtitle'] = subtitle      
            
            # Author and author link
            author, author_link = '', ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sumpage-header__authors")))
                a = wait(div, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
                author = a.get_attribute('textContent').strip()
                author_link = a.get_attribute('href').strip()
            except:
                try:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sumpage-review-header__biblio-details")))
                    text = div.get_attribute('textContent').replace('\n', '').strip()
                    if '•' in text:
                        text = text.split('•')
                        author = text[0].strip()
                except:
                    pass           
                
            details['Author'] = author            
            details['Author Link'] = author_link            
         
            # release date & publisher
            date, publisher = '', ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sumpage-header__edition")))
                publisher = wait(div, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('textContent').strip()
                date = wait(div, 2).until(EC.presence_of_element_located((By.TAG_NAME, "span"))).get_attribute('textContent').strip()
                
            except:
                try:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sumpage-header__edition")))
                    text = div.get_attribute('textContent').replace('\n', '').strip()
                    if ',' in text:
                        text = text.split(',')
                        publisher = text[0].strip()
                        date = text[-1].strip()
                except:
                    try:
                        div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sumpage-review-header__biblio-details")))
                        text = div.get_attribute('textContent').replace('\n', '').strip()
                        if '•' in text:
                            text = text.split('•')
                            if len(text) == 3:
                                publisher = text[1].strip()
                                date = text[2].strip()
                                date = int(date)
                            elif len(text) == 2:
                                date = text[1].strip()
                                date = int(date)
                    except:
                        pass              
                
            details['Publisher'] = publisher            
            details['Publication Year'] = date              
           
            # number of pages and ISBN
            npages, ISBN = '', ''
            try:
                # pressing on more button
                button = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//a[@class='sumpage-header__more-biblio-link']")))
                driver.execute_script("arguments[0].click();", button)
                time.sleep(1)

                info = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//div[@id='sumpage-header__editiondetails']"))).get_attribute('textContent').strip()
                elems = info.split('\n')
                for j, elem in enumerate(elems):
                        if 'ISBN:' in elem:
                            ISBN = elems[j+1].strip()
                        elif 'Pages:' in elem:
                            npages = int(elems[j+1].strip())
            except:
                pass           
                
            details['ISBN'] = ISBN            
            details['Number Of Pages'] = npages
            
            # rating
            rating = ''
            try:
                rating = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//span[@itemprop='ratingValue']"))).get_attribute('textContent').strip()
                rating = int(rating)
            except:
                pass           
                
            details['Editorial Rating'] = rating   
 
            # qualities
            qualities = ''
            try:
                lis = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.sumpage-valuation__qualities-element")))
                for li in lis:
                    qualities += li.get_attribute('textContent').strip()
                    qualities += ', '
            except:
                pass           
                
            details['Qualities'] = qualities[:-2]    
  
            # number of likes
            nlikes = ''
            try:
                nlikes = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//span[@class='sumpage-actionbar__label js-summary-like-count']"))).get_attribute('textContent').strip()
                nlikes = int(nlikes)
            except:
                pass           
                
            details['Number Of Likes'] = nlikes            
                  
            # Amazon link
            details['Amazon link'] = ''          
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sumpage-header__fulltext")))
                button = wait(div, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
                driver.execute_script("arguments[0].click();", button)
                time.sleep(1)
                buttons = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[class='btn btn-outline-primary']")))
                for butt in buttons:
                    if "Amazon.com" in butt.get_attribute('textContent'):
                        driver.get(butt.get_attribute('href'))
                        details['Amazon link'] = driver.current_url
                        break
            except:
                pass           
                
            # appending the output to the datafame        
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except:
            pass

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'getabstract.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    login_username = ''
    login_pass = ''
    data = scrape_getabstract(path, login_username, login_pass)

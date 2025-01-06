import re
import pymongo
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Define the WebDriver setup function
def setup_driver():
    service = Service("chromedriver/chromedriver.exe")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(service=service, options=options)

# Function to find raw URLs
def finding_raw_urls_from_base(url):
    driver = setup_driver()
    driver.get(url)
    WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'a')))
    html = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(html, 'html.parser')
    links = soup.find_all('a', href=True)
    raw_urls = {link['href'] for link in links if link['href'].startswith("https://www.moneycontrol.com/news/business/")}
    return list(raw_urls)

# Function to categorize URLs into different lists
def extract_urls(raw_urls):
    stock_urls = []
    market_urls = []
    next_page_urls = []
    ipo_urls = []
    other_urls = []
    
    for link in raw_urls:
        if link.startswith("https://www.moneycontrol.com/news/business/stocks/page"):
            next_page_urls.append(link)
        elif link.startswith("https://www.moneycontrol.com/news/business/stocks/"):
            stock_urls.append(link)
        elif link.startswith("https://www.moneycontrol.com/news/business/markets/"):
            market_urls.append(link)
        elif link.startswith("https://www.moneycontrol.com/news/business/ipo/"):
            ipo_urls.append(link)
        else:
            other_urls.append(link)
    
    return stock_urls, market_urls, next_page_urls, ipo_urls, other_urls

# Regular expression for validating stock URLs
regex = r'https:\/\/www\.moneycontrol\.com\/news\/business\/stocks\/[^\/\s]+(?:\.[a-z]{2,6})(?:[\/\?].*)?'

# Function to extract article data
def extract_data(url):
    driver = setup_driver()
    driver.get(url)
    WebDriverWait(driver, 60).until(lambda d: d.execute_script("return document.readyState") == "complete")
    
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    driver.quit()

    news = {}

    # Extracting article details
    title = soup.find('h1', class_="article_title")
    news["title"] = title.text.strip() if title else "No Title"
    
    desc = soup.find('h2', class_='article_desc')
    news["desc"] = desc.text.strip() if desc else "No Description"
    
    date_time_div = soup.find('div', class_="article_schedule")
    if date_time_div:
        span_tag = date_time_div.find('span')
        date = span_tag.text.strip() if span_tag else "No Date"
        news["date"] = date
        news["datetime"] = date_time_div.text.strip()
    
    # Extracting paragraphs
    paragraphs_list = []
    paragrphs_div = soup.find('div', class_="content_wrapper")
    if paragrphs_div:
        paragraph_tags = paragrphs_div.find_all('p')
        for p in paragraph_tags:
            para_text = p.text.strip()
            if len(para_text) < 50 or re.search(r"(click\s+here|disclaimer|modal|window|advertisement|investment\s+tips)", para_text, re.IGNORECASE):
                continue
            paragraphs_list.append(para_text)
    
    news["content"] = paragraphs_list
    
    # Extracting stock name
    stock_name = soup.find('a', class_="stock-name")
    news["stock_name"] = stock_name.text.strip() if stock_name else "No Stock Name"
    
    return news

# MongoDB setup
myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["new_db"]
mycol = mydb['raw_news']

# Main function to extract stock URLs and data
def main():
    raw_urls = finding_raw_urls_from_base("https://www.moneycontrol.com/news/business/stocks/")
    # raw_urls = finding_raw_urls_from_base("https://www.moneycontrol.com/news/business/stocks/page-30")
    stock_urls, _, _, _, _ = extract_urls(raw_urls)
    
    # Filter stock URLs based on the regex pattern
    final_stocks_urls = [url for url in stock_urls if re.match(regex, url)]
    
    # Extract data for each stock URL and store it in MongoDB
    for url in final_stocks_urls:
        data = extract_data(url)
        x = mycol.insert_one(data)
        print(f"Inserted document with ID: {x.inserted_id}")

# Run the main function
if __name__ == "__main__":
    main()

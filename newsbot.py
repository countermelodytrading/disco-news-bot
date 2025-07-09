import snscrape.modules.twitter as sntwitter
import requests
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time
import logging
import traceback
import urllib.request
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIG ---
from dotenv import load_dotenv
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
TWITTER_USERS = ['zerohedge', 'unusual_whales', 'KobeissiLetter', 'POTUS', 'realDonaldTrump', 'Newsquawk', 'WatcherGuru']
TRUTH_SOCIAL_URLS = [
    'https://truthsocial.com/@realDonaldTrump',
    'https://truthsocial.com/@POTUS'
]
KEYWORDS = ['tariff', 'israel', 'iran', 'russia', 'ukraine', 'elon musk', 'aapl', 'nvda', 'tsla']
KEYWORDS = [kw.lower() for kw in KEYWORDS]
LOOKBACK_MINUTES = 2
CACHE_FILE = 'seen_posts.json'

# --- POLLING INTERVALS (in seconds) ---
TWITTER_POLL_INTERVAL = 20
TRUTH_POLL_INTERVAL = 90

# --- LOGGING ---
logging.basicConfig(filename='newsbot.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

# --- CACHE ---
try:
    with open(CACHE_FILE, 'r') as f:
        seen_posts = set(json.load(f))
except:
    seen_posts = set()

def save_cache():
    with open(CACHE_FILE, 'w') as f:
        json.dump(list(seen_posts), f)

# --- DISCORD SEND FUNCTION ---
def send_to_discord(source, headline):
    post_hash = f"{source}:{headline}".lower().strip()
    if post_hash in seen_posts:
        return
    seen_posts.add(post_hash)
    save_cache()

    message = f"{source} : {headline}"
    payload = {"content": message}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
        logging.info(f"Sent to Discord: {message}")
    except Exception as e:
        logging.error(f"Error sending to Discord: {e}")

# --- TWITTER SCRAPE ---
def scrape_twitter():
    cutoff_time = datetime.utcnow() - timedelta(minutes=LOOKBACK_MINUTES)
    for user in TWITTER_USERS:
        try:
            query = f"from:{user}"
            for tweet in sntwitter.TwitterSearchScraper(query).get_items():
                if tweet.date < cutoff_time:
                    break
                text = tweet.content.lower()
                if any(keyword in text for keyword in KEYWORDS):
                    send_to_discord(user, tweet.content)
        except Exception as e:
            logging.error(f"Error scraping Twitter for {user}: {e}\n{traceback.format_exc()}")

# --- TRUTH SOCIAL SCRAPE WITH SELENIUM ---
def scrape_truth_social():
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    for url in TRUTH_SOCIAL_URLS:
        try:
            driver.get(url)
            time.sleep(5)  # Wait for dynamic content to load
            posts = driver.find_elements(By.CSS_SELECTOR, 'div')
            for post in posts:
                text = post.text.strip().lower()
                if any(keyword in text for keyword in KEYWORDS) and 10 < len(text) < 500:
                    send_to_discord("TruthSocial", text[:240] + ("..." if len(text) > 240 else ""))
        except Exception as e:
            logging.error(f"Error scraping Truth Social {url}: {e}\n{traceback.format_exc()}")

    driver.quit()

# --- MAIN LOOP ---
def main():
    logging.info("News bot is starting up.")
    send_to_discord("System", "✅ News bot is live and monitoring.")

    last_truth_check = 0
    last_twitter_check = 0

    while True:
        now = time.time()

        if now - last_twitter_check >= TWITTER_POLL_INTERVAL:
            try:
                scrape_twitter()
                last_twitter_check = now
            except Exception as e:
                logging.error(f"Twitter scrape error: {e}\n{traceback.format_exc()}")

        if now - last_truth_check >= TRUTH_POLL_INTERVAL:
            try:
                scrape_truth_social()
                last_truth_check = now
            except Exception as e:
                logging.error(f"Truth Social scrape error: {e}\n{traceback.format_exc()}")

        time.sleep(5)

if __name__ == "__main__":
    main()

import snscrape.modules.twitter as sntwitter
import requests
import re
from datetime import datetime, timedelta
import time
import logging
import traceback
import os
import json

# --- CONFIG ---
from dotenv import load_dotenv
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
TWITTER_USERS = ['zerohedge', 'unusual_whales', 'KobeissiLetter', 'POTUS', 'realDonaldTrump', 'Newsquawk', 'WatcherGuru']
KEYWORDS = ['tariff', 'israel', 'iran', 'russia', 'ukraine', 'elon musk', 'aapl', 'nvda', 'tsla']
KEYWORDS = [kw.lower() for kw in KEYWORDS]
LOOKBACK_MINUTES = 2
CACHE_FILE = 'seen_posts.json'

# --- POLLING INTERVAL ---
TWITTER_POLL_INTERVAL = 20

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

# --- MAIN LOOP ---
def main():
    logging.info("News bot is starting up.")
    send_to_discord("System", "✅ News bot is live and monitoring.")

    last_twitter_check = 0

    while True:
        now = time.time()

        if now - last_twitter_check >= TWITTER_POLL_INTERVAL:
            try:
                scrape_twitter()
                last_twitter_check = now
            except Exception as e:
                logging.error(f"Twitter scrape error: {e}\n{traceback.format_exc()}")

        time.sleep(5)

if __name__ == "__main__":
    main()

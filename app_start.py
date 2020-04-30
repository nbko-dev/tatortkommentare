import tweepy as tw
import re
import datetime, time
import urllib.request, urllib.error, urllib.parse
import ssl
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen
from flask import Flask, render_template, request, abort
import os, json

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Get Twitter API Access Token & Key
secret_file = os.path.join('./', 'secrets.json')

with open(secret_file) as f:
    secrets = json.loads(f.read())

def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        raise abort(404, description="Resource not found")

CONSUMER_KEY = get_secret("CONSUMER_KEY")
CONSUMER_SECRET = get_secret("CONSUMER_SECRET")
ACCESS_TOKEN = get_secret("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = get_secret("ACCESS_TOKEN_SECRET")

# Create Handler
auth = tw.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)

# Require Access
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# Create Twitter API
api = tw.API(auth, wait_on_rate_limit=True)

# URL
url = 'https://www.daserste.de/unterhaltung/krimi/tatort/sendung/index.html'
html = urlopen(url, context=ctx).read()
soup = bs(html, "html.parser")
date = soup.find("span", {"style": "float: right;"}).get_text(strip=True)

# Define the search term and the date_since date as variables
search_words = "@tatort"
date_since = date[6:] + "-" + date[3:5] + "-" + date[:2]
date_until = date[6:] + "-" + date[3:5] + "-" + str(int(date[:2])+1)
findaddress = soup.find("ul", {"class": "list"}).li.a['href']
episode = "https://www.daserste.de" + str(findaddress)
subject = soup.find("ul", {"class": "list"}).li.a.get_text(strip=True)
subject_split = re.search(r'(\w.+)\W\w.+\W', subject).group()[:-1]
commissioner = re.search(r'(\w.+)\((\w+)\)', subject).group(1)
location = re.search(r'(\w.+)\((\w+)\)', subject).group(2)

# Collect tweets
tweets = tw.Cursor(api.search,
                   q=search_words+"-filter:retweets",
                   lang="de",
                   since=date_since,
                   until=date_until,
                   tweet_mode='extended').items(100)

# Iterate and print tweets
result = list()
for tweet in tweets:
    result.append({"id": "@" + tweet.user.screen_name, "tweet_date": tweet.created_at.strftime("%d.%m.%y"), "tweet": tweet.full_text})

# Render the index page
app = Flask(__name__, template_folder = './templates', static_folder = './templates/static')
app.config["DEBUG"] = True

@app.route('/', methods=['GET','POST'])
def index():
    return render_template('index.html', result=result, subject=subject_split, commissioner=commissioner,
                           location=location, date=date, episode=episode)

port = int(os.environ.get('PORT', 5000))

if __name__ == '__main__':
    app.run(port)

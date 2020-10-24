# Telegram-Twitter-Bot

This projects aims to make a [Telegram](https://telegram.org) bot that forwards [Twitter](https://twitter.com/) updates to people, groups, channels, or whatever Telegram comes up with!

This is an updated version of the [telegram-twitter-bot](https://github.com/franciscod/telegram-twitter-forwarder-bot) which is build to be an AIO bot.


## Credits

This is based on:
- [telegram-twitter-forwarder-bot](https://github.com/franciscod/telegram-twitter-forwarder-bot)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [tweepy](https://github.com/tweepy/tweepy)
- [peewee](https://github.com/coleifer/peewee)
- python, pip, etc.


## How do I run this?

**The code has been updated and tested on python 3.8**

1. clone this repo
2. fill main.py with api keys (see next readme section)
3. create your virtualenv, activate it, etc, e.g.:
    ```
    virtualenv -p python3 venv
    . venv/bin/activate
    ```
4. `pip install -r requirements.txt`
5. run it! `python main.py`

## API Keys

First, you'll need a Telegram Bot Token, you can get it via BotFather ([more info here](https://core.telegram.org/bots)).

Also, setting this up will need an Application-only authentication token from Twitter ([more info here](https://dev.twitter.com/oauth/application-only)). Optionally, you can provide a user access token and secret.

You can get this by creating a Twitter App [here](https://apps.twitter.com/).

Bear in mind that if you don't have added a mobile phone to your Twitter account you'll get this:

>You must add your mobile phone to your Twitter profile before creating an application. Please read https://support.twitter.com/articles/110250-adding-your-mobile-number-to-your-account-via-web for more information.

Get a consumer key, consumer secret, access token and access token secret (the latter two are optional), fill in your keys inside **main.py** (Starting Line 11), source it, and then run the bot!
```
# Telegram Token
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_KEY"
# Twitter API
TWITTER_CONSUMER_KEY = "YOUR_TWITTER_CONSUMER_KEY"
TWITTER_CONSUMER_SECRET = "YOUR_TWITTER_CONSUMER_SECRET"
# optionally
TWITTER_ACCESS_TOKEN = "YOUR_TWITTER_ACCESS_TOKEN"
TWITTER_ACCESS_TOKEN_SECRET = "YOUR_TWITTER_ACCESS_TOKEN_SECRET"
```

## TODO:

- Add More Logging Features
- Fix Migration Mechanism
- Fix Twitter Fetch Delay
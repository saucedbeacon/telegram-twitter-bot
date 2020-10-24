import logging

import tweepy
from telegram.ext import CommandHandler
from telegram.ext import Updater, CallbackContext

from bot import TwitterForwarderBot
from botConversationHandlers import *
from commands import *
from job import FetchAndSendTweetsJob

# Telegram Token
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_KEY"
# Twitter API
TWITTER_CONSUMER_KEY = "YOUR_TWITTER_CONSUMER_KEY"
TWITTER_CONSUMER_SECRET = "YOUR_TWITTER_CONSUMER_SECRET"
# optionally
TWITTER_ACCESS_TOKEN = "YOUR_TWITTER_ACCESS_TOKEN"
TWITTER_ACCESS_TOKEN_SECRET = "YOUR_TWITTER_ACCESS_TOKEN_SECRET"


def callbackBot(context: CallbackContext):
    FetchAndSendTweetsJob().run(t_bot)


if __name__ == '__main__':

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.WARNING)

    logging.getLogger(TwitterForwarderBot.__name__).setLevel(logging.DEBUG)
    logging.getLogger(FetchAndSendTweetsJob.__name__).setLevel(logging.DEBUG)

    # initialize Twitter API
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)

    try:
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
    except KeyError:
        print("Either TWITTER_ACCESS_TOKEN or TWITTER_ACCESS_TOKEN_SECRET "
              "environment variables are missing. "
              "Tweepy will be initialized in 'app-only' mode")

    twapi = tweepy.API(auth)
    t_bot = TwitterForwarderBot(TELEGRAM_BOT_TOKEN, twapi)

    # initialize telegram API
    updater = Updater(bot=t_bot, use_context=True)
    dispatcher = updater.dispatcher

    # set commands
    dispatcher.add_handler(CommandHandler('add', cmd_add_handler))
    dispatcher.add_handler(cmd_add_channel_handler)
    dispatcher.add_handler(cmd_add_username_handler)
    dispatcher.add_handler(cmd_add_group_handler)

    dispatcher.add_handler(CommandHandler('unsub', cmd_unsub_handler))
    dispatcher.add_handler(cmd_unsub_telegram_handler)
    dispatcher.add_handler(cmd_unsub_twitter_handler)

    dispatcher.add_handler(CommandHandler('start', cmd_start))
    dispatcher.add_handler(CommandHandler('help', cmd_help))
    dispatcher.add_handler(CommandHandler('ping', cmd_ping))

    # put job
    queue = updater.job_queue
    queue.run_repeating(callbackBot, interval=20, first=10)

    # poll
    updater.start_polling()
    updater.idle()

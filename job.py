import html
import logging
import re
from datetime import datetime
from threading import Event

import tweepy
from telegram.error import TelegramError
from telegram.ext import Job, CallbackContext

from models import TwitterUser, Tweet, Subscription, TelegramChat

INFO_CLEANUP = {
    'NOTFOUND': "Your subscription to @{} was removed because that profile doesn't exist anymore. Maybe the account's "
                "name changed?",
    'PROTECTED': "Your subscription to @{} was removed because that profile is protected and can't be fetched.",
}


class FetchAndSendTweetsJob(Job):
    # Twitter API rate limit parameters
    LIMIT_WINDOW = 10 * 60
    LIMIT_COUNT = 300
    MIN_INTERVAL = 60
    TWEET_BATCH_INSERT_COUNT = 100

    @property
    def interval(self):
        return 300

    def __init__(self, context=None):
        self.repeat = True
        self.context = context
        self.name = self.__class__.__name__
        self.__name__ = self.__class__.__name__
        self._remove = Event()
        self._enabled = Event()
        self._enabled.set()
        self.logger = logging.getLogger(self.name)

    def run(self, context: CallbackContext):
        self.logger.debug("Fetching tweets...")
        tweet_rows = []
        # fetch the tw users' tweets
        tw_users = list((TwitterUser.select()
                         .join(Subscription)
                         .group_by(TwitterUser)
                         .order_by(TwitterUser.last_fetched)))
        updated_tw_users = []
        users_to_cleanup = []

        for tw_user in tw_users:
            try:
                if tw_user.last_tweet_id == 0:
                    # get just the latest tweet
                    self.logger.debug(
                        "Fetching latest tweet by {}".format(tw_user.screen_name))
                    tweets = context.tw.user_timeline(
                        screen_name=tw_user.screen_name,
                        count=1,
                        tweet_mode='extended',
                        include_rts=True)
                else:
                    # get the fresh tweets
                    self.logger.debug(
                        "Fetching new tweets from {}".format(tw_user.screen_name))
                    tweets = context.tw.user_timeline(
                        screen_name=tw_user.screen_name,
                        since_id=tw_user.last_tweet_id,
                        tweet_mode='extended',
                        include_rts=True)
                updated_tw_users.append(tw_user)
            except tweepy.error.TweepError as e:
                sc = e.response.status_code
                if sc == 429:
                    self.logger.debug("- Hit ratelimit, breaking.")
                    break

                if sc == 401:
                    users_to_cleanup.append((tw_user, 'PROTECTED'))
                    self.logger.debug("- Protected tweets here. Cleaning up this user")
                    continue

                if sc == 404:
                    users_to_cleanup.append((tw_user, 'NOTFOUND'))
                    self.logger.debug("- 404? Maybe screen name changed? Cleaning up this user")
                    continue

                self.logger.debug(
                    "- Unknown exception, Status code {}".format(sc))
                continue

            for tweet in tweets:
                self.logger.debug("- Got tweet: {} - Reply ID: {}".format(tweet.full_text, tweet.in_reply_to_status_id))

                # If tweet contains media, get it back
                video_urls = self.getVideo(tweet)
                photo_urls = self.getMedia(tweet)

                # Clean tweet text that contains URLs 
                tweet_text = self.cleanTweetText(tweet)

                # Get Retweet's Full text
                tweet_text = self.getFullRetweetText(tweet_text, tweet)

                # If in_reply_to_status_id belongs to the same user, forward the tweet
                # Meaning we set the is_Reply to none.
                tweet_is_reply = tweet.in_reply_to_status_id
                tweet_is_reply = self.checkReplySameUser(tweet, context, tw_user, tweet_is_reply)

                # Clean the photo_urls and video_url in order to get a string
                # We separate the urls with ;
                photo_urls_string = self.cleanMediaUrl(photo_urls)
                video_urls_string = self.cleanMediaUrl(video_urls)

                tw_data = {
                    'tw_id': tweet.id,
                    'text': tweet_text,
                    'is_Reply': tweet_is_reply,
                    'created_at': tweet.created_at,
                    'twitter_user': tw_user,
                    'photo_url': photo_urls_string,
                    'video_url': video_urls_string
                }

                try:
                    t = Tweet.get(Tweet.tw_id == tweet.id)
                    self.logger.warning("Got duplicated tw_id on this tweet:")
                    self.logger.warning(str(tw_data))
                except Tweet.DoesNotExist:
                    tweet_rows.append(tw_data)

                if len(tweet_rows) >= self.TWEET_BATCH_INSERT_COUNT:
                    Tweet.insert_many(tweet_rows).execute()
                    tweet_rows = []

        TwitterUser.update(last_fetched=datetime.now()) \
            .where(TwitterUser.id << [tw.id for tw in updated_tw_users]).execute()

        if not updated_tw_users:
            return

        if tweet_rows:
            Tweet.insert_many(tweet_rows).execute()

        # send the new tweets to subscribers
        subscriptions = list(Subscription.select()
                             .where(Subscription.tw_user << updated_tw_users))
        for s in subscriptions:
            # are there new tweets? send em all!

            if s.last_tweet_id == 0:  # didn't receive any tweet yet
                try:
                    tw = s.tw_user.tweets.select() \
                        .order_by(Tweet.tw_id.desc()) \
                        .first()
                    if tw is None:
                        self.logger.warning("Something fishy is going on here...")
                    else:
                        context.send_tweet(s.tg_chat, tw, s.forward_reply, s.link_twitter_usernames_hashtags)
                        # save the latest tweet sent on this subscription
                        s.last_tweet_id = tw.tw_id
                        s.save()
                except IndexError:
                    self.logger.debug("- No tweets available yet on {}".format(s.tw_user.screen_name))

                continue

            if s.tw_user.last_tweet_id > s.last_tweet_id:
                self.logger.debug("- Some fresh tweets here!")
                for tw in (s.tw_user.tweets.select()
                        .where(Tweet.tw_id > s.last_tweet_id)
                        .order_by(Tweet.tw_id.asc())
                ):
                    context.send_tweet(s.tg_chat, tw, s.forward_reply)

                # save the latest tweet sent on this subscription
                s.last_tweet_id = s.tw_user.last_tweet_id
                s.save()
                continue

            self.logger.debug("- No new tweets here.")

        self.logger.debug("Starting tw_user cleanup")
        if not users_to_cleanup:
            self.logger.debug("- Nothing to cleanup")
        else:
            for tw_user, reason in users_to_cleanup:
                self.logger.debug("- Cleaning up subs on user @{}, {}".format(tw_user.screen_name, reason))
                message = INFO_CLEANUP[reason].format(tw_user.screen_name)
                subs = list(tw_user.subscriptions)
                for s in subs:
                    chat = s.tg_chat
                    if chat.delete_soon:
                        self.logger.debug("- - skipping because of delete_soon chatid={}".format(chat_id))
                        continue
                    chat_id = chat.chat_id
                    chat_username = chat.username
                    self.logger.debug("- - bye on chatid={}".format(chat_id))
                    s.delete_instance()

                    try:
                        context.sendMessage(chat_id=chat_username, text=message)
                    except TelegramError as e:
                        self.logger.info("Couldn't send unsubscription notice of {} to chat {}: {}".format(
                            tw_user.screen_name, chat_id, e.message
                        ))

                        delet_this = None

                        if e.message == 'Bad Request: group chat was migrated to a supergroup chat':
                            delet_this = True

                        if e.message == "Unauthorized":
                            delet_this = True

                        if delet_this:
                            self.logger.info("Marking chat for deletion")
                            chat.delete_soon = True
                            chat.save()

            self.logger.debug("- Cleaning up TwitterUser @{}".format(tw_user.screen_name, reason))
            tw_user.delete_instance()

            self.logger.debug("- Cleanup finished")

        self.logger.debug("Cleaning up TelegramChats marked for deletion")
        for chat in TelegramChat.select().where(TelegramChat.delete_soon == True):
            chat.delete_instance(recursive=True)
            self.logger.debug("Deleting chat {}".format(chat.chat_id))

    def cleanMediaUrl(self, media_urls):
        media_string = ''
        for media in media_urls:
            media_string = media_string + media + ";"
        return media_string

    def checkReplySameUser(self, tweet, context, tw_user, tweet_is_reply):
        if tweet.in_reply_to_status_id is not None:
            tempTweet = context.tw.get_status(tweet.in_reply_to_status_id)
            if (str(tempTweet.user.screen_name)).lower() == (str(tw_user.screen_name)).lower():
                self.logger.debug(" {} is the same as {} - Tweet is a reply to a thread."
                                  .format(tempTweet.user.screen_name, tw_user.screen_name))
                tweet_is_reply = None
        return tweet_is_reply

    def getFullRetweetText(self, tweet_text, tweet):
        if tweet_text.startswith("RT @") == True or tweet_text.startswith("rt @") == True:
            self.logger.debug("Tweet is a RT - {}".format(tweet.retweeted_status.full_text))
            rtUsername = tweet_text.split(':')[0]
            tweet_text = rtUsername + ": " + tweet.retweeted_status.full_text
        return tweet_text

    def cleanTweetText(self, tweet):
        tweet_text = html.unescape(tweet.full_text)
        for url_entity in tweet.entities['urls']:
            expanded_url = url_entity['expanded_url']
            indices = url_entity['indices']
            display_url = tweet.full_text[indices[0]:indices[1]]
            tweet_text = tweet_text.replace(display_url, expanded_url)
        return tweet_text

    def getMedia(self, tweet):
        extensions = ('.jpg', '.jpeg', '.png', '.gif')
        pattern = '[(%s)]$' % ')('.join(extensions)
        photo_urls = []
        count = 0

        if 'media' in tweet.entities:
            for media in tweet.extended_entities['media']:
                try:
                    photo_urls.append(media['media_url_https'])
                    count = count + 1
                except:
                    self.logger.debug("No more media in tweet.")
        else:
            for url_entity in tweet.entities['urls']:
                expanded_url = url_entity['expanded_url']
                if re.search(pattern, expanded_url):
                    photo_urls.append(expanded_url)
                    break

        if photo_urls:
            for photo_url in photo_urls:
                self.logger.debug("- - Found media URL in tweet: " + photo_url)
        return photo_urls

    def getVideo(self, tweet):
        video_urls = []
        if 'media' in tweet.entities:
            for media in tweet.extended_entities['media']:
                if 'video_info' in media:
                    video = media['video_info']
                    video = video['variants'][-1]
                    video_urls.append(video['url'])
        return video_urls

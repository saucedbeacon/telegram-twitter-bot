import logging

import telegram
from telegram import Bot, InputMediaPhoto, InputMediaVideo
from telegram.error import TelegramError

from models import TelegramChat
from util import prepare_tweet_text


class TwitterForwarderBot(Bot):

    def __init__(self, token, tweepy_api_object, update_offset=15):
        super().__init__(token=token)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing")
        self.update_offset = update_offset
        self.tw = tweepy_api_object

    @property
    def interval(self):
        return 300

    def reply(self, update, text, *args, **kwargs):
        self.sendMessage(chat_id=update.message.chat.id, text=text, *args, **kwargs)

    def isReply(self, tweet):
        if tweet.is_Reply is not None:
            return True
        else:
            return False

    def send_tweet(self, chat, tweet, forward_reply, link_twitter_usernames_hashtags):
        try:
            # Do not forward reply tweets if setting is set to No (0)
            if forward_reply == 0 and self.isReply(tweet):
                self.logger.debug("Tweet {} is a reply, I will not forward it.".format(
                    tweet.tw_id))
            else:
                self.logger.debug("Sending tweet {} to chat {}...".format(
                    tweet.tw_id, chat.username
                ))

                tweet_text = self.prepare_twitter_text_message(link_twitter_usernames_hashtags, tweet)

                photo_url = ''
                if tweet.video_url:
                    video_url = self.cleanVideoArray(tweet)

                    if len(video_url) >= 2:
                        mediaList = self.prepareMultipleVideos(video_url, tweet_text)
                        self.sendMultipleMedia(chat, mediaList)

                    else:
                        self.sendSingleVideo(video_url, chat, tweet_text)

                elif tweet.photo_url:
                    photo_url = self.cleanPhotoArray(tweet)

                    if len(photo_url) >= 2:
                        mediaList = self.prepareMultiplePhotos(photo_url, tweet_text)
                        self.sendMultipleMedia(chat, mediaList)

                    else:
                        self.sendSinglePhoto(photo_url, chat, tweet_text)

                else:
                    self.sendMessageOnly(chat, photo_url, tweet_text)

        except TelegramError as e:
            self.logger.info("Couldn't send tweet {} to chat {}: {}".format(
                tweet.tw_id, chat.username, e.message
            ))

            delete_this = None

            if e.message == 'Bad Request: group chat was migrated to a supergroup chat':
                delete_this = True

            if e.message == "Unauthorized":
                delete_this = True

            if delete_this:
                self.logger.info("Marking chat for deletion")
                chat.delete_soon = True
                chat.save()

    def prepare_twitter_text_message(self, link_twitter_usernames_hashtags, tweet):
        if link_twitter_usernames_hashtags:
            return prepare_tweet_text(tweet.text)
        else:
            return tweet.text

    def cleanPhotoArray(self, tweet):
        photo_url = tweet.photo_url
        photo_url = list(photo_url.split(";"))
        photo_url = photo_url[:len(photo_url) - 1]
        return photo_url

    def cleanVideoArray(self, tweet):
        video_url = tweet.video_url
        video_url = list(video_url.split(";"))
        video_url = video_url[:len(video_url) - 1]
        return video_url

    def prepareMultiplePhotos(self, photo_url, tweet_text):
        mediaList = []
        count = 0
        for photo in photo_url:
            if count == 0:
                photoOBject = InputMediaPhoto(media=photo,
                                              caption="""{text}""".format(text=tweet_text),
                                              parse_mode=telegram.ParseMode.MARKDOWN_V2)
            else:
                photoOBject = InputMediaPhoto(media=photo)
            mediaList.append(photoOBject)
            count = count + 1
        return mediaList

    def prepareMultipleVideos(self, video_url, tweet_text):
        mediaList = []
        count = 0
        for video in video_url:
            if count == 0:
                photoOBject = InputMediaVideo(media=video,
                                              caption="""{text}""".format(text=tweet_text),
                                              parse_mode=telegram.ParseMode.MARKDOWN_V2)
            else:
                photoOBject = InputMediaVideo(media=video)
            mediaList.append(photoOBject)
            count = count + 1
        return mediaList

    def sendMessageOnly(self, chat, photo_url, tweet_text):
        self.sendMessage(
            chat_id=chat.username,
            disable_web_page_preview=False,
            text="""{text}"""
                .format(
                link_preview=photo_url,
                text=tweet_text,
            ),
            parse_mode=telegram.ParseMode.MARKDOWN_V2)

    def sendSingleVideo(self, video_url, chat, tweet_text):
        video_url = video_url[0]
        self.logger.debug("Sending media {}".format(video_url))
        self.sendVideo(
            chat_id=chat.username,
            video=video_url,
            caption="""{text}"""
                .format(
                text=tweet_text,
            parse_mode=telegram.ParseMode.MARKDOWN_V2,
            supports_streaming=True))

    def sendSinglePhoto(self, photo_url, chat, tweet_text):
        photo_url = photo_url[0]
        self.logger.debug("Sending media {}".format(photo_url))
        self.sendPhoto(
            chat_id=chat.username,
            photo=photo_url,
            caption="""{text}"""
                .format(
                text=tweet_text,
            ),
            parse_mode=telegram.ParseMode.MARKDOWN_V2)

    def sendMultipleMedia(self, chat, mediaList):
        self.sendMediaGroup(
            chat_id=chat.username,
            media=mediaList)


    def get_chat(self, tg_chat):
        db_chat, _created = TelegramChat.get_or_create(
            chat_id=tg_chat.id,
        )
        return db_chat

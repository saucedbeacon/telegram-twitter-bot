import re


def escape_markdown(text):
    """Helper function to escape telegram markup symbols"""
    escape_chars = '\*_`\['
    return re.sub(r'([%s])' % escape_chars, r'\\\1', text)


def markdown_twitter_usernames(text):
    """Restore markdown escaped usernames and make them link to twitter"""
    return re.sub(r'@([A-Za-z0-9_\\]+)',
                  lambda s: '[@{username}](https://twitter.com/{username})'
                  .format(username=s.group(1).replace(r'\_', '_')),
                  text)


def markdown_twitter_hashtags(text):
    """Restore markdown escaped hashtags and make them link to twitter"""
    return re.sub(r'#([^\s]*)',
                  lambda s: '[#{tag}](https://twitter.com/hashtag/{tag})'
                  .format(tag=s.group(1).replace(r'\_', '_')),
                  text)


def prepare_tweet_text(text):
    """Do all escape things for tweet text"""
    res = escape_markdown(text)
    res = markdown_twitter_usernames(res)
    res = markdown_twitter_hashtags(res)
    return res


def prepare_telegram_username(telegram_username):
    if telegram_username.startswith('@'):
        return telegram_username
    else:
        return "@" + telegram_username

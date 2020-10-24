import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ConversationHandler

from addToDb import get_tw_user, get_tele_user
from models import Subscription, TelegramChat, TwitterUser
from util import prepare_telegram_username

NAME_REPLY, TWITTER_REPLY, FORWARD_REPLY, SUB_LINK_TWITTER = range(4)


def cmd_ping(update, context):
    update.message.reply_text('Pong!')


def cmd_start(update, context):
    update.message.reply_text(
        """Hello! This bot lets you subscribe to twitter accounts and forward their tweets either to here or to a group. 
        Check out /help for more info.""")


def cmd_help(update, context):
    update.message.reply_text("""
Hello! This bot forwards you updates from twitter streams!
Here's the commands:
- /add - adds a new telegram account or group
- /unsub - unsubscribes from users
- /help - view help text
""",disable_web_page_preview=True, parse_mode=telegram.ParseMode.MARKDOWN)


def cmd_add_keyboard():
    keyboard = [
        [InlineKeyboardButton("Username", callback_data=str("USERNAME"))],
        [InlineKeyboardButton("Channel", callback_data=str("CHANNEL"))],
        [InlineKeyboardButton("Group", callback_data=str("GROUP"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def cmd_unsub_keyboard():
    keyboard = [
        [InlineKeyboardButton("Telegram", callback_data=str("TELEGRAM"))],
        [InlineKeyboardButton("Twitter", callback_data=str("TWITTER"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def sub_forward_reply_keyboard():
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=str("TRUE"))],
        [InlineKeyboardButton("No", callback_data=str("FALSE"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def sub_link_twitter_keyboard():
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=str("TRUE"))],
        [InlineKeyboardButton("No", callback_data=str("FALSE"))]
    ]
    return InlineKeyboardMarkup(keyboard)


def cmd_add_reply_keyboard():
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Done")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return reply_keyboard


def cmd_add_handler(update, context):
    update.message.reply_text(
        "Press on what type you want to add.",
        reply_markup=cmd_add_keyboard())


def cmd_unsub_handler(update, context):
    update.message.reply_text(
        "Press on what type of service you want to unsub.",
        reply_markup=cmd_unsub_keyboard())


def sub_forward_reply_handler(update, context):
    update.message.reply_text(
        "Would you like to forward replies from this/those account?",
        reply_markup=sub_forward_reply_keyboard())


def cmd_add_username(update, context):
    query = update.callback_query
    context.user_data['user_id'] = query.message.chat.id

    change_cmd_add_button_message(update, context, "Adding New User(s) To Bot")

    context.bot.send_message(chat_id=context.user_data['user_id'], text="""
This Does NOT take in your username, rather your telegram user ID.
Enter one or several user IDs separated by a space.

If you do not know how to get your user ID, follow X
Or use @userinfobot
""", reply_markup=cmd_add_reply_keyboard())
    return NAME_REPLY


def cmd_add_channel(update, context):
    query = update.callback_query
    context.user_data['user_id'] = query.message.chat.id

    change_cmd_add_button_message(update, context, "Adding New Channel(s) To Bot")

    context.bot.send_message(chat_id=context.user_data['user_id'], text="""
Enter one or several channel names separated by a space.

Make sure to add the bot as an admin to the channel.
""", reply_markup=cmd_add_reply_keyboard())
    return NAME_REPLY


def cmd_add_group(update, context):
    query = update.callback_query
    context.user_data['user_id'] = query.message.chat.id

    change_cmd_add_button_message(update, context, "Adding New Group(s) To Bot")

    context.bot.send_message(chat_id=context.user_data['user_id'], text="""
This Does NOT take in your groupname, rather your telegram group ID.
Enter one or several group IDs separated by a space.

Make sure to add the bot as an admin to the group.
""", reply_markup=cmd_add_reply_keyboard())
    return NAME_REPLY


def change_cmd_add_button_message(update, context, textMessage):
    context.bot.edit_message_text(
        text=textMessage,
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        reply_markup=None
    )
    context.bot.answer_callback_query(update.callback_query.id, text='')


def change_cmd_add_button_keyboard(update, context, textMessage):
    context.bot.edit_message_text(
        text=textMessage,
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        reply_markup=sub_link_twitter_keyboard()
    )
    context.bot.answer_callback_query(update.callback_query.id, text='')


def get_names(update):
    user_input = update.message.text
    user_input = user_input.split()
    return user_input


def is_telegram_account_already_inDB(telegram_username):
    return TelegramChat.select().where(TelegramChat.username == telegram_username).count() == 1


def not_found_reply(not_found, reply):
    reply += "Sorry, I didn't find username{} {}\n\n".format(
        "" if len(not_found) == 1 else "s",
        ", ".join(not_found)
    )
    return reply


def already_subscribed_reply(already_subscribed, reply):
    reply += "You're already subscribed to {}\n\n".format(
        ", ".join(already_subscribed)
    )
    return reply


def successfully_subscribed_reply(successfully_subscribed, reply):
    reply += "I've added your subscription to {}".format(
        ", ".join(successfully_subscribed)
    )
    return reply


def check_subscription_status(not_found, already_subscribed, successfully_subscribed, reply):
    if len(not_found) != 0:
        reply += not_found_reply(not_found, reply)

    if len(already_subscribed) != 0:
        reply += already_subscribed_reply(already_subscribed, reply)

    if len(successfully_subscribed) != 0:
        reply += successfully_subscribed_reply(successfully_subscribed, reply)

    return reply


def cmd_add_telegram_account(update, context, isChannel):
    user_input = get_names(update)

    if len(user_input) < 1:
        update.message.reply_text("Please Enter a valid username.")
        return

    not_found = []
    already_subscribed = []
    successfully_subscribed = []
    telegram_users_list = []

    for telegram_username in user_input:
        telegram_username = telegram_username.lower()
        if isChannel:
            telegram_username = prepare_telegram_username(telegram_username)

        telegram_users_list.append(telegram_username)
        context.user_data['telegram'] = telegram_users_list

        if is_telegram_account_already_inDB(telegram_username):
            already_subscribed.append(telegram_username)
        else:
            telegram_DB_user = get_tele_user(telegram_username)

            if telegram_DB_user is None:
                not_found.append(telegram_username)
            else:
                successfully_subscribed.append(telegram_username)

    reply = ""
    reply = check_subscription_status(not_found, already_subscribed, successfully_subscribed, reply)
    twitter_reply = """
Now please enter one or more twitter account usernames separated by space:
"""
    update.message.reply_text(reply + twitter_reply)


def cmd_add_channel_helper(update, context):
    cmd_add_telegram_account(update, context, True)
    return TWITTER_REPLY


def cmd_add_username_helper(update, context):
    cmd_add_telegram_account(update, context, False)
    return TWITTER_REPLY


def cmd_add_group_helper(update, context):
    cmd_add_telegram_account(update, context, False)
    return TWITTER_REPLY


def sub_forward_reply(update, context):
    context.user_data['twitter'] = update.message.text.split()
    sub_forward_reply_handler(update, context)
    return FORWARD_REPLY


def sub_link_twitter_username(update, context):
    context.user_data['forward_reply'] = str_to_bool(update.callback_query.data)
    ask_message = """
Would you like to change twitter usernames and hashtags to point to the actual twitter URLs?
CAREFUL: This will sometimes preview the usernames/hashtags and not the links inside the tweet."""
    change_cmd_add_button_keyboard(update, context, ask_message)
    return SUB_LINK_TWITTER


def is_telegram_sub_to_twitter(tw_user, telegram_user):
    return Subscription.select().where(
        Subscription.tw_user == tw_user,
        Subscription.tg_chat == telegram_user).count() == 1


def str_to_bool(user_input):
    return user_input == "TRUE"


def cmd_sub(update, context):
    sub_link_twitter = update.callback_query.data
    sub_link_twitter = str_to_bool(sub_link_twitter)

    forward_reply = context.user_data['forward_reply']
    twitter_usernames = context.user_data['twitter']
    telegram_usernames = context.user_data['telegram']

    if len(twitter_usernames) < 1 or len(telegram_usernames) < 1:
        update.message.reply_text("Invalid Command")
        return
    not_found = []
    already_subscribed = []
    successfully_subscribed = []

    for twitter_username in twitter_usernames:
        for telegram_username in telegram_usernames:
            twitter_username = twitter_username.lower()
            tw_user = get_tw_user(twitter_username)

            telegram_username = telegram_username.lower()
            telegram_user = get_tele_user(telegram_username)

            if tw_user is None:
                not_found.append(twitter_username)
                continue

            if is_telegram_sub_to_twitter(tw_user, telegram_user):
                already_subscribed.append(str(twitter_username) + " " + str(telegram_username))
                continue

            Subscription.create(tg_chat=telegram_user, tw_user=tw_user, forward_reply=forward_reply,
                                link_twitter_usernames_hashtags=sub_link_twitter)
            successfully_subscribed.append(str(twitter_username) + " -> " + str(telegram_username))

    reply = ""
    reply = check_subscription_status(not_found, already_subscribed, successfully_subscribed, reply)
    change_cmd_add_button_message(update, context, reply)
    return ConversationHandler.END


def cmd_unsub_telegram(update, context):
    query = update.callback_query

    context.bot.send_message(chat_id=query.message.chat.id, text="""
CAREFUL! This deletes all records of a telegram account/group/channel.

Unsub one/several telegram Users/Groups/Channels.
Enter one or several UserID/GroupID/channelName separated by a space.
Or type each username/ID on a new line.
NOTE: Please enter telegram channel names with a starting @ (EG: @test)

When done, type Done.
""", reply_markup=cmd_add_reply_keyboard())
    return NAME_REPLY


def cmd_unsub_twitter(update, context):
    query = update.callback_query

    context.bot.send_message(chat_id=query.message.chat.id, text="""
CAREFUL! This deletes all records of a twitter account.

Unsub From one/several twitter accounts.
Enter one or several twitter usernames separated by a space.
Or type each username/ID on a new line.

When done, type Done.
""", reply_markup=cmd_add_reply_keyboard())
    return NAME_REPLY


def is_telegram_account_not_sub_to_any_twitter(telegram_username_DB):
    return Subscription.select().where(Subscription.tg_chat == telegram_username_DB).count() == 0


def is_telegram_account_not_inDB(telegram_username):
    return TelegramChat.select().where(TelegramChat.username == telegram_username).count() == 0


def cmd_unsub_telegram_helper(update, context):
    user_telegram_input = get_names(update)

    if len(user_telegram_input) < 1:
        update.message.reply_text("Enter a valid username/ID.")
        return
    not_found = []
    successfully_unsubscribed = []

    for telegram_username in user_telegram_input:
        telegram_username = telegram_username.lower()
        telegram_username_DB = get_tele_user(telegram_username)

        if telegram_username_DB is None or (is_telegram_account_not_sub_to_any_twitter(telegram_username_DB)
                                            and is_telegram_account_not_inDB(telegram_username)):
            not_found.append(telegram_username)
            continue

        if not (is_telegram_account_not_sub_to_any_twitter(telegram_username_DB)):
            Subscription.delete().where(
                Subscription.tg_chat == telegram_username_DB).execute()

        if not is_telegram_account_not_inDB:
            TelegramChat.delete().where(
                TelegramChat.username == telegram_username).execute()

        successfully_unsubscribed.append(telegram_username)

    reply = ""
    reply = unsub_status(not_found, successfully_unsubscribed, reply)
    update.message.reply_text(reply)


def is_twitter_account_not_sub_to_any_telegram(tw_username_DB):
    return Subscription.select().where(Subscription.tw_user == tw_username_DB).count() == 0


def is_twitter_account_not_inDB(tw_username):
    return TwitterUser.select().where(TwitterUser.screen_name == tw_username).count() == 0


def cmd_unsub_twitter_helper(update, context):
    user_twitter_input = get_names(update)

    if len(user_twitter_input) < 1:
        update.message.reply_text("Enter a valid username.")
        return
    not_found = []
    successfully_unsubscribed = []

    for tw_username in user_twitter_input:
        tw_username = tw_username.lower()
        tw_username_DB = get_tw_user(tw_username)

        if tw_username_DB is None or (is_twitter_account_not_sub_to_any_telegram(tw_username_DB)
                                      and is_twitter_account_not_inDB(tw_username)):
            not_found.append(tw_username)
            continue

        if not (is_twitter_account_not_sub_to_any_telegram(tw_username_DB)):
            Subscription.delete().where(
                Subscription.tw_user == tw_username_DB).execute()

        if not (is_twitter_account_not_inDB(tw_username)):
            TwitterUser.delete().where(
                TwitterUser.screen_name == tw_username).execute()

        successfully_unsubscribed.append(tw_username)

    reply = ""
    reply = unsub_status(not_found, successfully_unsubscribed, reply)
    update.message.reply_text(reply)


def not_found_subscription_reply(not_found, reply):
    reply += "I didn't find any subscription to {}\n\n".format(
        ", ".join(not_found)
    )
    return reply


def successfully_unsubscribed_reply(successfully_unsubscribed, reply):
    reply += "You are no longer subscribed to {}".format(
        ", ".join(successfully_unsubscribed)
    )
    return reply


def unsub_status(not_found, successfully_unsubscribed, reply):
    if len(not_found) != 0:
        reply += not_found_subscription_reply(not_found, reply)
    if len(successfully_unsubscribed) != 0:
        reply += successfully_unsubscribed_reply(successfully_unsubscribed, reply)

    return reply


def handle_chat(bot, update):
    bot.reply(update, "Hey! Use commands to talk with me, please! See /help")

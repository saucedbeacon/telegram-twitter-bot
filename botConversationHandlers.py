import re

from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, Filters

from commands import cmd_add_channel, cmd_add_username, cmd_add_channel_helper, cmd_sub, cmd_help, \
    cmd_add_username_helper, cmd_add_group, cmd_add_group_helper, cmd_unsub_telegram, cmd_unsub_telegram_helper, \
    cmd_unsub_twitter, cmd_unsub_twitter_helper, sub_forward_reply, sub_link_twitter_username

NAME_REPLY, TWITTER_REPLY, FORWARD_REPLY, SUB_LINK_TWITTER = range(4)

cmd_add_channel_handler = ConversationHandler(
    allow_reentry=True,
    entry_points=[CallbackQueryHandler(cmd_add_channel, pattern='CHANNEL')],
    states={
        NAME_REPLY: [
            MessageHandler(
                Filters.text & ~(Filters.command | Filters.regex((re.compile(r'^Done$', re.IGNORECASE)))),
                cmd_add_channel_helper)
        ],
        TWITTER_REPLY: [
            MessageHandler(
                Filters.text & ~(Filters.command | Filters.regex((re.compile(r'^Done$', re.IGNORECASE)))),
                sub_forward_reply)
        ],
        FORWARD_REPLY: [
            CallbackQueryHandler(sub_link_twitter_username)
        ],
        SUB_LINK_TWITTER: [
            CallbackQueryHandler(cmd_sub)
        ],
    },
    fallbacks=[MessageHandler(Filters.regex((re.compile(r'^Done$', re.IGNORECASE))), cmd_help)],
)

cmd_add_username_handler = ConversationHandler(
    allow_reentry=True,
    entry_points=[CallbackQueryHandler(cmd_add_username, pattern='USERNAME')],
    states={
        NAME_REPLY: [
            MessageHandler(
                Filters.text & ~(Filters.command | Filters.regex((re.compile(r'^Done$', re.IGNORECASE)))),
                cmd_add_username_helper)
        ],
        TWITTER_REPLY: [
            MessageHandler(
                Filters.text & ~(Filters.command | Filters.regex((re.compile(r'^Done$', re.IGNORECASE)))),
                sub_forward_reply)
        ],
        FORWARD_REPLY: [
            CallbackQueryHandler(sub_link_twitter_username)
        ],
        SUB_LINK_TWITTER: [
            CallbackQueryHandler(cmd_sub)
        ],
    },
    fallbacks=[MessageHandler(Filters.regex((re.compile(r'^Done$', re.IGNORECASE))), cmd_help)],
)

cmd_add_group_handler = ConversationHandler(
    allow_reentry=True,
    entry_points=[CallbackQueryHandler(cmd_add_group, pattern='GROUP')],
    states={
        NAME_REPLY: [
            MessageHandler(
                Filters.text & ~(Filters.command | Filters.regex((re.compile(r'^Done$', re.IGNORECASE)))),
                cmd_add_group_helper)
        ],
        TWITTER_REPLY: [
            MessageHandler(
                Filters.text & ~(Filters.command | Filters.regex((re.compile(r'^Done$', re.IGNORECASE)))),
                sub_forward_reply)
        ],
        FORWARD_REPLY: [
            CallbackQueryHandler(sub_link_twitter_username)
        ],
        SUB_LINK_TWITTER: [
            CallbackQueryHandler(cmd_sub)
        ],
    },
    fallbacks=[MessageHandler(Filters.regex((re.compile(r'^Done$', re.IGNORECASE))), cmd_help)],
)

cmd_unsub_telegram_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(cmd_unsub_telegram, pattern='TELEGRAM')],
    states={
        NAME_REPLY: [
            MessageHandler(
                Filters.text & ~(Filters.command | Filters.regex((re.compile(r'^Done$', re.IGNORECASE)))),
                cmd_unsub_telegram_helper)
        ],
    },
    fallbacks=[MessageHandler(Filters.regex((re.compile(r'^Done$', re.IGNORECASE))), cmd_help)],
)

cmd_unsub_twitter_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(cmd_unsub_twitter, pattern='TWITTER')],
    states={
        NAME_REPLY: [
            MessageHandler(
                Filters.text & ~(Filters.command | Filters.regex((re.compile(r'^Done$', re.IGNORECASE)))),
                cmd_unsub_twitter_helper)
        ],
    },
    fallbacks=[MessageHandler(Filters.regex((re.compile(r'^Done$', re.IGNORECASE))), cmd_help)],
)
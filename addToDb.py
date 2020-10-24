from models import TelegramChat, TwitterUser


def get_tw_user(tw_username):
    tw_username = tw_username.lower()
    db_user, _created = TwitterUser.get_or_create(
        screen_name=tw_username,
    )

    if not _created:
        if db_user.screen_name != tw_username:
            db_user.screen_name = tw_username
            db_user.save()

    return db_user


def get_tele_user(telegram_username):
    telegram_username = telegram_username.lower()
    db_user, _created = TelegramChat.get_or_create(
        username=telegram_username,
    )

    if not _created:
        if db_user.username != telegram_username:
            db_user.username = telegram_username
            db_user.save()

    return db_user

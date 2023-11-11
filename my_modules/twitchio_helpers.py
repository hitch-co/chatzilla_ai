from my_modules import my_logging

logger = my_logging.create_logger(
    dirname='log', 
    logger_name='logger_twitchio_helpers',
    debug_level='DEBUG',
    mode='w',
    stream_logs=False
    )

def get_string_of_users(usernames_list) -> str:
    users_in_users_list = list(set([username for username in usernames_list]))
    users_in_users_list_text = "', '".join(users_in_users_list)
    logger.debug(f"These are the users in message list text: {users_in_users_list_text}")
    return users_in_users_list_text

from my_modules import my_logging

logger = my_logging.my_logger(dirname='log', 
                              logger_name='logger_twitchio_helpers',
                              debug_level='DEBUG',
                              mode='w',
                              stream_logs=False)

def extract_name_from_rawdata(message_rawdata):
    start_index = message_rawdata.find(":") + 1
    end_index = message_rawdata.find("!")
    if start_index == 0 or end_index == -1:
        return 'unknown_name - see message.raw_data for details'
    else:
        return message_rawdata[start_index:end_index]
    
def extract_usernames_string_from_chat_history(msg_history_list) -> str:
    users_in_messages_list = list(set([message['role'] for message in msg_history_list]))
    users_in_messages_list_text = "', '".join(users_in_messages_list)
    logger.debug(f"These are the users in message list text: {users_in_messages_list_text}")
    return users_in_messages_list_text

def extract_usernames_string_from_usernames_list(usernames_list) -> str:
    users_in_users_list = list(set([username for username in usernames_list]))
    users_in_users_list_text = "', '".join(users_in_users_list)
    logger.debug(f"These are the users in message list text: {users_in_users_list_text}")
    return users_in_users_list_text

def get_channel_chatters(broadcaster_id='194006544',
                         moderator_id='950051618',
                         client_id='q78eqthr7quxpsd0q44ssu136p18p4',
                         bearer_token=None):
    import requests

    url = 'https://api.twitch.tv/helix/chat/chatters'
    params = {
        'broadcaster_id': broadcaster_id,
        'moderator_id': moderator_id
    }
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Client-Id': client_id
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        print("Success:", response.json())
    else:
        print("Failed:", response.status_code, response.text)

    return response
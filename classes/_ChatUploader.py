import os
import requests
from google.cloud import bigquery 

from my_modules.utils import get_datetime_formats
from my_modules.config import load_env, load_yaml
import json
from my_modules import my_logging
from my_modules.utils import write_json_to_file

load_env()

class TwitchChatData:
    def __init__(self):
        self.twitch_broadcaster_author_id = os.getenv('TWITCH_BROADCASTER_AUTHOR_ID')
        self.twitch_bot_moderator_id = os.getenv('TWITCH_BOT_MODERATOR_ID')
        self.twitch_bot_client_id = os.getenv('TWITCH_BOT_CLIENT_ID')
        self.twitch_bot_access_token = os.getenv('TWITCH_BOT_ACCESS_TOKEN')
        self.bq_client = bigquery.Client()

        self.logger = my_logging.my_logger(dirname='log', 
                                           logger_name='logger_ChatUploader',
                                           debug_level='DEBUG',
                                           mode='w',
                                           stream_logs=False)
        self.logger.debug('TwitchChatData initialized.')

    def get_channel_viewers(self,
                            bearer_token=None):
        self.logger.debug('Getting channel viewers with bearer_token: %s', bearer_token)
        base_url='https://api.twitch.tv/helix/chat/chatters'
        params = {
            'broadcaster_id': self.twitch_broadcaster_author_id,
            'moderator_id': self.twitch_bot_moderator_id
        }
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Client-Id': self.twitch_bot_client_id
        }
        response = requests.get(base_url, params=params, headers=headers)
        self.logger.debug('Received response: %s', response)

        write_json_to_file(self, response.json(), variable_name_text='channel_viewers', dirname='log/get_chatters_data')
        self.logger.debug('Wrote json file...')
        return response

    def process_channel_viewers(self, response):
        self.logger.debug('Processing channel viewers response: %s', response)
        timestamp = get_datetime_formats()['sql_format']
        if response.status_code == 200:
            self.logger.debug("Response.json(): %s", response.json())
            response_json = response.json()
            channel_viewers_list_dict = response_json['data']
            for item in channel_viewers_list_dict:
                item['timestamp'] = timestamp
            self.logger.debug(f"channel_viewers_list_dict:")
            self.logger.debug(channel_viewers_list_dict)
        else:
            self.logger.error("Failed: %s, %s", response.status_code, response.text)
            response.raise_for_status()
        return channel_viewers_list_dict

    def generate_bq_query(self, table_id, channel_viewers_list_dict):
        
        testing_list_dict = [
            {
                "user_id": "654447790",
                "user_login": "aliceydra",
                "user_name": "aliceydra"
            },
            {
                "user_id": "105166207",
                "user_login": "streamlabs",
                "user_name": "Streamlabs"
            }
            ]

        # Start building the MERGE statement
        merge_query = f"""
            MERGE {table_id} AS target
            USING (
                SELECT
                    user_id,
                    user_login,
                    user_name,
                    timestamp AS last_seen
                FROM
                    UNNEST([%s]) AS channel_viewers(user_id, user_login, user_name, timestamp)
            ) AS source
            ON target.user_id = source.user_id
            WHEN MATCHED THEN
                UPDATE SET
                    target.user_login = source.user_login,
                    target.user_name = source.user_name,
                    target.last_seen = source.last_seen
            WHEN NOT MATCHED THEN
                INSERT (user_id, user_login, user_name, last_seen)
                VALUES(source.user_id, source.user_login, source.user_name, source.last_seen);
        """

        # Serialize the channel_viewers_list_dict to a JSON string
        channel_viewers_json_str = json.dumps(channel_viewers_list_dict)

        # Format the merge_query with the JSON string
        formatted_query = merge_query % channel_viewers_json_str

        return formatted_query
    

# if __name__ == '__main__':
#     chatdataclass = TwitchChatData()
#     chatdataclass.get_channel_viewers()
#     self.logger.debug('Execution completed.')
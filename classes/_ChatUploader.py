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

    # def process_channel_viewers(self, channel_viewers_response):
    #     self.logger.debug('Processing channel viewers response: %s', channel_viewers_response)
    #     channel_viewers_response
    #     if channel_viewers_response.status_code == 200:
    #         self.logger.debug("Success: %s", channel_viewers_response.json())
    #         channel_viewers_response['timestamp'] = get_datetime_formats()['sql_format']
    #     else:
    #         self.logger.error("Failed: %s, %s", channel_viewers_response.status_code, channel_viewers_response.text)
    #         channel_viewers_response.raise_for_status()
    #     channel_viewers_response_json = channel_viewers_response.json()
    #     return channel_viewers_response_json

    # def process_viewers_data(self, channel_viewers_response_json):
    #     self.logger.debug('Processing viewers data: %s', channel_viewers_response_json)
    #     # Extracting relevant fields from each item in the data list
    #     viewers_records_list = [
    #         {
    #             'user_id': item['user_id'],
    #             'user_login': item['user_login'],
    #             'user_name': item['user_name'],
    #             'last_seen': channel_viewers_response_json['timestamp']
    #         } for item in channel_viewers_response_json['data']
    #         ]
    #     return viewers_records_list #List of dicts ready for BigQuery

    # def process_chatter_data(self, chatters_response_object):
    #     self.logger.debug('Processing chatter data: %s', chatters_response_object)
    #     # Assuming interactions_data is derived somehow, or it could be an empty list if not used
    #     interactions_records_list = {
    #         'user_id': chatters_response_object['user_id'],
    #         'interaction_type':chatters_response_object['interaction_type'],
    #         'interaction_contents':chatters_response_object['interaction_contents']
    #         } 
    #     interactions_records_list['timestamp'] = chatters_response_object['timestamp']
    #     return interactions_records_list

    # def send_to_bq(self, table_id, data):
    #     self.logger.debug('Sending data to BigQuery, table_id: %s, data: %s', table_id, data)
    #     table = self.bq_client.get_table(table_id)
    #     errors = self.bq_client.insert_rows_json(table, data)
    #     self.logger.debug('Insertion errors: %s', errors)
    #     # if errors:
    #     #     self.logger.error('BigQueryError: %s', errors)
    #     #     raise BigQueryError(errors)

# if __name__ == '__main__':
#     chatdataclass = TwitchChatData()
#     chatdataclass.get_channel_viewers()
#     self.logger.debug('Execution completed.')
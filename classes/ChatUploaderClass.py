import os
import requests
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from my_modules.utils import get_datetime_formats
from my_modules.config import load_env, load_yaml
import json
from my_modules import my_logging
from my_modules.utils import write_json_to_file, write_query_to_file




class TwitchChatData:
    def __init__(self):

        load_env()

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

        #also set in twitch_bot.py
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'config/keys/eh-talkzilla-ai-1bcb1963d5b4.json'

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

        # Build the UNION ALL part of the query
        union_all_query = " UNION ALL ".join([
            f"SELECT '{viewer['user_id']}' as user_id, '{viewer['user_login']}' as user_login, "
            f"'{viewer['user_name']}' as user_name, PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', '{viewer['timestamp']}') as last_seen"
            for viewer in channel_viewers_list_dict
        ])
        write_query_to_file(formatted_query=union_all_query, 
                            dirname='log/queries',
                            queryname='unionall')
        
        # Add the union all query to our final query to be sent to BQ jobs
        merge_query = f"""
            MERGE {table_id} AS target
            USING (
                {union_all_query}
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
        write_query_to_file(formatted_query=merge_query, 
                            dirname='log/queries',
                            queryname='final')
        
        return merge_query
    
    def send_to_bq(self, query):
        # Initialize a BigQuery client
        client = bigquery.Client()

        try:
            # Start the query job
            self.logger.info("Starting BigQuery job...")
            query_job = client.query(query)

            # Wait for the job to complete (this will block until the job is done)
            self.logger.info(f"Executing query: {query}")
            query_job.result()

            # Log job completion
            self.logger.info(f"Query job {query_job.job_id} completed successfully.")

        except GoogleAPIError as e:
            # Log any API errors
            self.logger.error(f"BigQuery job failed: {e}")

        except Exception as e:
            # Log any other exceptions
            self.logger.error(f"An unexpected error occurred: {e}")

        else:
            # Optionally, get and log job statistics
            job_stats = query_job.query_plan
            self.logger.info(f"Query plan: {job_stats}")

# if __name__ == '__main__':
#     chatdataclass = TwitchChatData()
#     chatdataclass.get_channel_viewers()
#     self.logger.debug('Execution completed.')
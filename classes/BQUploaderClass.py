import os
import requests
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed

from classes.ConfigManagerClass import ConfigManager

from my_modules import my_logging
from my_modules import utils

runtime_debug_level = 'WARNING'

class BQUploader:
    def __init__(self):
        #logger
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='logger_BQUploader',
            debug_level=runtime_debug_level,
            mode='w',
            stream_logs=True
            )
        self.logger.debug('BQUploader Logger initialized.')

        self.config = ConfigManager.get_instance()

        # env variables 
        #TODO: get_channel_viewers should probably be a separate helper
        # module/function/class to work with the twitch API directly
        self.twitch_broadcaster_author_id = self.config.twitch_broadcaster_author_id
        self.twitch_bot_moderator_id = self.config.twitch_bot_moderator_id
        self.twitch_bot_client_id = self.config.twitch_bot_client_id

        # chatters endpoint
        self.twitch_get_chatters_endpoint = 'https://api.twitch.tv/helix/chat/chatters'

        #Build the client
        self.bq_client = bigquery.Client()

        #Users lists
        self.channel_viewers_list_dict_temp = []
        self.channel_viewers_queue = []

    #TODO: get_channel_viewers should probably be a separate helper
    # module/function/class to work with the twitch API directly
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
    def get_channel_viewers(
        self,
        bearer_token=None
        ) -> object:

        self.logger.debug(f'Getting channel viewers with bearer_token')
        base_url=self.twitch_get_chatters_endpoint
        params = {
            'broadcaster_id': self.twitch_broadcaster_author_id,
            'moderator_id': self.twitch_bot_moderator_id
        }
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Client-Id': self.twitch_bot_client_id
        }
        response = requests.get(base_url, params=params, headers=headers)
        self.logger.debug(f'Received response: {response}')

        utils.write_json_to_file(
            response.json(), 
            variable_name_text='channel_viewers', 
            dirname='log/get_chatters_data'
            )
        self.logger.debug('Wrote response.json() to file...')

        if response.status_code == 200:
            self.logger.debug("Response.json(): %s", response.json())
        else:
            self.logger.error("Failed: %s, %s", response.status_code, response.text)
            response.raise_for_status()

        return response

    def process_channel_viewers(self, response) -> list[dict]:
        self.logger.debug('Processing channel viewers response')
        timestamp = utils.get_datetime_formats()['sql_format']
        
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

    def queue_channel_viewers(self, records: list[dict]) -> None:
        updated_channel_viewers_queue = self.channel_viewers_queue
        updated_channel_viewers_queue.extend(records)

        df = pd.DataFrame(updated_channel_viewers_queue)
        df = df.sort_values(['user_id', 'timestamp'])
        df = df.drop_duplicates(subset='user_id', keep='last')
        self.logger.info(f'channel_viewers_queue deduplicated has {len(df)} rows')

        self.channel_viewers_queue = df.to_dict('records')

    def generate_bq_users_query(self, table_id, records: list[dict]) -> str:

        # Build the UNION ALL part of the query
        union_all_query = " UNION ALL ".join([
            f"SELECT '{viewer['user_id']}' as user_id, '{viewer['user_login']}' as user_login, "
            f"'{viewer['user_name']}' as user_name, PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', '{viewer['timestamp']}') as last_seen"
            for viewer in records
        ])
        utils.write_query_to_file(formatted_query=union_all_query, 
                            dirname='log/queries',
                            queryname='channelviewers_query')
        
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
        utils.write_query_to_file(formatted_query=merge_query, 
                            dirname='log/queries',
                            queryname='channelviewers_query_final')
        
        self.logger.info("The users table query was generated")
        self.logger.debug("This is the users table merge query:")
        self.logger.debug(merge_query)
        return merge_query

    def fetch_users(self, table_id) -> list[dict]:
        query = f"""
        SELECT user_id, user_login, user_name
        FROM `{table_id}`
        """

        # Execute the query
        query_job = self.bq_client.query(query)

        # Process the results
        results = []
        for row in query_job:
            results.append({
                "user_id": row.user_id,
                "user_login": row.user_login,
                "user_name": row.user_name
            })

        return results

    #TODO: get_channel_viewers should probably be a separate helper
    # module/function/class to work with the twitch API directly
    def get_process_queue_create_channel_viewers_query(
            self, 
            bearer_token,
            table_id,
            response = None
            ) -> str:
        
        #Response from twitch API
        if response == None:
            response = self.get_channel_viewers(bearer_token=bearer_token)
        
        #retrieves list of dicts
        channel_viewers_records = self.process_channel_viewers(response=response)
        
        #queues/updates the self.channel_viewers_queue
        self.queue_channel_viewers(records=channel_viewers_records)

        #generates a query based on the queued viewers
        channel_viewers_query = self.generate_bq_users_query(
            table_id=table_id,
            records=self.channel_viewers_queue
            )

        return channel_viewers_query

    def generate_bq_user_interactions_records(self, records: list[dict]) -> list[dict]:
        rows_to_insert = []
        for record in records:
            user_id = record.get('user_id')
            channel = record.get('channel')
            content = record.get('content')
            timestamp = record.get('timestamp')
            user_badges = record.get('badges')
            color = record.get('tags').get('color', '') if record.get('tags') else ''
            
            row = {
                "user_id": user_id,
                "channel": channel,
                "content": content,
                "timestamp": timestamp,
                "user_badges": user_badges,
                "color": color                
            }
            rows_to_insert.append(row)

        self.logger.debug("These are the user interactions records (rows_to_insert):")
        self.logger.debug(rows_to_insert[0:2])
        return rows_to_insert   

    def send_recordsjob_to_bq(self, table_id, records:list[dict]) -> None:
        table = self.bq_client.get_table(table_id)
        errors = self.bq_client.insert_rows_json(table, records)     
        if errors:
            self.logger.error(f"Encountered errors while inserting rows: {errors}")
            self.logger.error("These are the records:")
            self.logger.error(records)
        else:
            self.logger.info(f"Rows successfully inserted into table_id: {table_id}")
            self.logger.debug("These are the records:")
            self.logger.debug(records)
            
    def send_queryjob_to_bq(self, query):
        try:
            # Start the query job
            self.logger.info("Starting BigQuery job...")
            query_job = self.bq_client.query(query)

            # Wait for the job to complete (this will block until the job is done)
            self.logger.info(f"Executing query...")
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

if __name__ == '__main__':
    chatdataclass = BQUploader()
    chatdataclass.get_channel_viewers()
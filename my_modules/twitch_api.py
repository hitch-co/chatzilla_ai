from tenacity import retry, stop_after_attempt, wait_fixed
import requests
import pandas as pd

from classes.ConfigManagerClass import ConfigManager

from my_modules import my_logging
from my_modules import utils

runtime_debug_level = 'INFO'

class TwitchAPI:
    def __init__(self):
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='logger_BQUploader',
            debug_level=runtime_debug_level,
            mode='w',
            stream_logs=True
            )
        self.config = ConfigManager.get_instance()

        self.twitch_broadcaster_author_id = self.config.twitch_broadcaster_author_id
        self.twitch_bot_moderator_id = self.config.twitch_bot_moderator_id
        self.twitch_bot_client_id = self.config.twitch_bot_client_id

        self.twitch_get_chatters_endpoint = 'https://api.twitch.tv/helix/chat/chatters'

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
    async def _fetch_channel_viewers(self, bearer_token) -> dict:
        try:
            base_url = self.twitch_get_chatters_endpoint
            params = {
                'broadcaster_id': self.twitch_broadcaster_author_id,
                'moderator_id': self.twitch_bot_moderator_id
            }
            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'Client-Id': self.twitch_bot_client_id
            }
            response = requests.get(base_url, params=params, headers=headers)

            if response.status_code == 200:
                self.logger.debug(f'Successfully retrieved channel viewers: {response.json()}')
                return response.json()
            else:
                self.logger.error(f'Failed to retrieve channel viewers: {response.status_code}, {response.text}')
                response.raise_for_status()
        except Exception as e:
            self.logger.exception(f'Error fetching channel viewers: {e}')
            return None
    
    async def retrieve_active_usernames(self, bearer_token) -> list[str]:
        viewer_data = await self._fetch_channel_viewers(bearer_token)

        if viewer_data:
            current_users_in_session = viewer_data.get('data', [])
            current_user_names = [user['user_login'] for user in current_users_in_session]
            self.logger.debug(f"current_user_names: {current_user_names}")
            return current_user_names
        else:
            self.logger.warning("Failed to retrieve viewer data or data is empty.")
            return ['test_user']

    def _transform_viewer_data(self, viewer_data_json) -> list[dict]:
        self.logger.debug('Processing channel viewers data')
        timestamp = utils.get_datetime_formats()['sql_format']
        
        if viewer_data_json:
            channel_viewers_list_dict = viewer_data_json.get('data', [])
            for item in channel_viewers_list_dict:
                item['timestamp'] = timestamp
            self.logger.debug(f"channel_viewers_list_dict:")
            self.logger.debug(channel_viewers_list_dict)
        else:
            self.logger.error("Invalid viewer data provided to _transform_viewer_data")
            raise ValueError("Invalid viewer data provided to _transform_viewer_data")
        
        return channel_viewers_list_dict

    async def _enqueue_viewer_records(self, records: list[dict]) -> None:

        self.logger.debug(f'Enqueuing {len(records)} records to channel_viewers_queue')

        if hasattr(self, 'channel_viewers_queue') and self.channel_viewers_queue is not None:
            self.logger.debug(f'channel_viewers_queue has {len(self.channel_viewers_queue)} rows')

        # Initialize the queue if it doesn't exist
        if not hasattr(self, 'channel_viewers_queue') or self.channel_viewers_queue is None:
            self.channel_viewers_queue = []
            self.logger.debug(f'channel_viewers_queue initialized: {self.channel_viewers_queue}')

        # Extend the existing queue with new records
        self.channel_viewers_queue.extend(records)

        # Convert to DataFrame for sorting and deduplication
        df = pd.DataFrame(self.channel_viewers_queue)
        df = df.sort_values(['user_id', 'timestamp']).drop_duplicates(subset='user_id', keep='last')

        # Update the queue and log
        self.channel_viewers_queue = df.to_dict('records')
        self.logger.debug(f'channel_viewers_queue updated with {len(self.channel_viewers_queue)} rows')
        
    def _create_bigquery_merge_query(self, table_id, records: list[dict]) -> str:

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
        
        self.logger.debug("The users table query was generated")
        self.logger.debug("This is the users table merge query:")
        self.logger.debug(merge_query)
        return merge_query

    # LAST STEP: RUNNNER
    async def process_viewers_for_bigquery(self, bearer_token, table_id) -> str:
        viewer_data = await self._fetch_channel_viewers(bearer_token)

        if viewer_data:
            channel_viewers_records = self._transform_viewer_data(viewer_data)
            await self._enqueue_viewer_records(records=channel_viewers_records)
            channel_viewers_query = self._create_bigquery_merge_query(table_id, self.channel_viewers_queue)
            return channel_viewers_query
        else:
            self.logger.error("Failed to process viewers for BigQuery due to data retrieval failure.")
            return
    
# if __name__ == "__main__":
#     twitch_api = TwitchAPI()
#     twitch_api.logger.info('TwitchAPI initialized.')
#     twitch_api._fetch_channel_viewers(
#         bearer_token='
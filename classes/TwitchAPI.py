from tenacity import retry, stop_after_attempt, wait_fixed
import requests
import pandas as pd
import os

from classes.ConfigManagerClass import ConfigManager

from my_modules import my_logging
from my_modules import utils

runtime_debug_level = 'INFO'

class TwitchAPI:
    def __init__(self):
        self.logger = my_logging.create_logger(
            dirname='log', 
            logger_name='TwitchAPI',
            debug_level=runtime_debug_level,
            mode='w',
            stream_logs=True
            )
        self.config = ConfigManager.get_instance()

        self.TWITCH_API_BASE_URL = "https://api.twitch.tv/helix"
        self.USERS_ENDPOINT = "/users"
        self.MODERATORS_ENDPOINT = "/moderation/moderators"
        self.CHATTERS_ENDPOINT = "/chat/chatters"

        try:
            self.config.twitch_bot_user_id = self._get_and_set_user_id(
                #bearer_token=self.config.twitch_bot_access_token,
                bearer_token=os.getenv("TWITCH_BOT_ACCESS_TOKEN"), 
                login_name=self.config.twitch_bot_username
                )
            self.logger.debug(f"Login Name: {self.config.twitch_bot_username}")
            self.logger.debug(f"Resulting Bot User ID: {self.config.twitch_bot_user_id}")
        except Exception as e:
            self.logger.error(f"Failed to retrieve bot's user ID: {e}")
            self.config.twitch_bot_user_id = None

        try:
            self.config.twitch_broadcaster_user_id = self._get_and_set_user_id(
                #bearer_token=self.config.twitch_bot_access_token,
                bearer_token=os.getenv("TWITCH_BOT_ACCESS_TOKEN"),
                login_name=self.config.twitch_bot_channel_name
                )
            self.logger.debug(f"Broadcasters User ID: {self.config.twitch_broadcaster_user_id}")    
        except Exception as e:
            self.logger.error(f"Failed to retrieve broadcaster's user ID: {e}")
            self.config.twitch_broadcaster_user_id = None

    def _get_and_set_user_id(self, bearer_token, login_name):
        self.logger.info(f"Getting bot's user ID using token: {bearer_token}")

        # Twitch API authentication headers
        HEADERS = {
            "Client-ID": self.config.twitch_bot_client_id,
            "Authorization": f'Bearer {bearer_token}'
        }

        # Get the user ID of the bot
        url = f"{self.TWITCH_API_BASE_URL}{self.USERS_ENDPOINT}?login={login_name}"
        self.logger.debug(f"Users Endpoint: {url}")
        try:
            response = requests.get(url, headers=HEADERS)
            user_data = response.json()
            self.logger.debug(f"User Data: {user_data}")
        except Exception as e:
            self.logger.error(f"Failed to retrieve user data: {e}")
            return None

        # Set the broadcaster's user ID
        try:
            if user_data["data"]:
                user_id = user_data["data"][0]["id"]
                self.logger.debug(f"Bots User ID: {user_id}")
                return user_id
            else:
                return None
        except Exception as e:
            self.logger.error(f"Issue with user_data['data']: {e}")
            return None
                
    # def _get_moderators(self, bearer_token):

    #     # Twitch API authentication headers
    #     HEADERS = {
    #         "Client-ID": self.config.twitch_bot_client_id,
    #         "Authorization": f'Bearer {bearer_token}'
    #     }

    #     params = {
    #         'broadcaster_id': self.config.twitch_broadcaster_user_id
    #     }
    #     # Get the list of moderators for the channel
    #     url = f"{self.TWITCH_API_BASE_URL}{self.MODERATORS_ENDPOINT}"
    #     response = requests.get(url, params=params, headers=HEADERS)
    #     moderators_data = response.json()
    #     self.logger.debug('--------------------------------------------------------------------')
    #     self.logger.debug('--------------------------------------------------------------------')
    #     self.logger.debug('--------------------------------------------------------------------')
    #     self.logger.debug('--------------------------------------------------------------------')
    #     self.logger.debug(f"Moderators Endpoint: {url}")
    #     self.logger.debug(f"Params: {params}")
    #     self.logger.debug(f"Headers: {HEADERS}")
    #     self.logger.debug(f"Moderators Data response.json()logger.debug(): {moderators_data}")

    #     if moderators_data["data"]:
    #         moderators_list = [moderator["user_id"] for moderator in moderators_data["data"]]
    #         return moderators_list
    #     else:
    #         return []

    # def set_moderator_id_to_env(self, bearer_token):
    #     # Set bot's user ID
    #     self._get_and_set_user_id(bearer_token)
        
    #     if self.config.twitch_broadcaster_user_id:

    #         # Get list of moderators including the bot
    #         moderators = self._get_moderators(bearer_token)
    #         if bot_user_id in moderators:
    #             self.logger.debug(f"Bot is a moderator of the channel. Their ID is: {moderators[0]}")
    #             self.config.twitch_bot_moderator_id = moderators[0]
    #         else:
    #             self.logger.warning("Bot is not a moderator of the channel.")
    #     else:
    #         print("Failed to retrieve bot's user ID.")

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
    async def _fetch_channel_viewers(self, bearer_token) -> dict:

        try:
            chatters_endpoint_url = f"{self.TWITCH_API_BASE_URL}{self.CHATTERS_ENDPOINT}"
            params = {
                'broadcaster_id': self.config.twitch_broadcaster_user_id,
                'moderator_id': self.config.twitch_bot_user_id
            }
            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'Client-Id': self.config.twitch_bot_client_id
            }

            self.logger.debug(f'Chatters Endpoint: {chatters_endpoint_url}')
            self.logger.debug(f"Params: {params}")
            self.logger.debug(f"Headers: {headers}")

            response = requests.get(chatters_endpoint_url, params=params, headers=headers)

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
            return None

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

        # Initialize the queue if it doesn't exist
        if not hasattr(self, 'channel_viewers_queue') or self.channel_viewers_queue is None:
            self.channel_viewers_queue = []
            self.logger.debug(f'channel_viewers_queue initialized: {self.channel_viewers_queue}')
            
        if hasattr(self, 'channel_viewers_queue') and self.channel_viewers_queue is not None:
            self.logger.debug(f'channel_viewers_queue has {len(self.channel_viewers_queue)} rows')

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
            return None
    
if __name__ == "__main__":
    twitch_api = TwitchAPI()
    twitch_api.logger.info('TwitchAPI initialized.')
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

        # Twitch API Endpoints
        self.TWITCH_API_BASE_URL = "https://api.twitch.tv/helix"
        self.USERS_ENDPOINT = "/users"
        self.MODERATORS_ENDPOINT = "/moderation/moderators"
        self.CHATTERS_ENDPOINT = "/chat/chatters"

        # Channel Viewers Queue
        self.channel_viewers_queue = []

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
        self.logger.debug(f"Getting bot's user ID using token...")

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

    # # NOTE: that this won't work as the bot is not the broadcaster         
    # def _get_moderators(self, bearer_token) -> list[dict]:
    #     """
    #     Returns a list of dicts, each containing user_id, user_login, and user_name 
    #     for moderators of the broadcaster's channel.
    #     Requires that your token has the 'moderation:read' scope.
    #     """
    #     HEADERS = {
    #         "Client-ID": self.config.twitch_bot_client_id,
    #         "Authorization": f'Bearer {bearer_token}'
    #     }

    #     # Make sure we have a broadcaster ID to query
    #     if not self.config.twitch_broadcaster_user_id:
    #         self.logger.warning("No broadcaster user ID found; can't retrieve moderators.")
    #         return []

    #     params = {
    #         'broadcaster_id': self.config.twitch_broadcaster_user_id
    #     }

    #     url = f"{self.TWITCH_API_BASE_URL}{self.MODERATORS_ENDPOINT}"
    #     self.logger.debug(f"Fetching moderators from: {url}, params: {params}")

    #     try:
    #         response = requests.get(url, params=params, headers=HEADERS)
    #         if response.status_code != 200:
    #             self.logger.error(f"Failed to retrieve moderators. Status code: {response.status_code} | {response.text}")
    #             return []

    #         moderators_data = response.json()  # {'data': [...], 'pagination': ...}
    #         self.logger.debug(f"Moderators data response: {moderators_data}")

    #         if not moderators_data or "data" not in moderators_data:
    #             return []

    #         # Create a list of (user_id, user_login, user_name)
    #         moderators_list = [{
    #             "user_id": m["user_id"],
    #             "user_login": m["user_login"],
    #             "user_name": m["user_name"]
    #         } for m in moderators_data["data"]]

    #         if moderators_list:
    #             self.logger.info(f"Successfully retrieved {len(moderators_list)} moderators for this channel.")
    #         else:
    #             self.logger.warning("No moderators returned or retrieval failed. Check your token scopes or broadcaster ID.")

    #         return moderators_list

    #     except Exception as e:
    #         self.logger.error(f"Exception when retrieving moderators: {str(e)}", exc_info=True)
    #         return []

    def follow_twitch_user(self, target_login: str, bearer_token: str) -> bool:
        """
        Follows the target_login user from the bot account.
        Requires 'user:edit:follows' scope on the bot's bearer_token.
        Returns True if follow is successful, False otherwise.
        """
        # -- 1) Get the target user's ID from login
        headers = {
            "Client-ID": self.config.twitch_bot_client_id,
            "Authorization": f"Bearer {bearer_token}",
        }
        url_get_user = f"{self.TWITCH_API_BASE_URL}{self.USERS_ENDPOINT}?login={target_login}"
        try:
            resp = requests.get(url_get_user, headers=headers)
            if resp.status_code != 200:
                self.logger.error(f"Failed to retrieve user ID for {target_login} "
                                f"(status code: {resp.status_code}, text: {resp.text})")
                return False

            resp_json = resp.json()
            users_data = resp_json.get("data", [])
            if not users_data:
                self.logger.error(f"No user found for login: {target_login}")
                return False

            target_user_id = users_data[0]["id"]
            self.logger.debug(f"Target login '{target_login}' has user ID = {target_user_id}")

        except Exception as e:
            self.logger.error(f"Exception occurred while getting target user ID: {e}", exc_info=True)
            return False

        # -- 2) POST /users/follows to follow target user
        url_follow = f"{self.TWITCH_API_BASE_URL}/users/follows"
        data = {
            "from_id": self.config.twitch_bot_user_id,  # Bot's user ID
            "to_id": target_user_id                     # The user we want to follow
        }
        try:
            follow_resp = requests.post(url_follow, headers=headers, json=data)

            # Twitch responds with 204 (No Content) on success
            if follow_resp.status_code == 204:
                self.logger.info(f"Bot successfully followed user '{target_login}' ({target_user_id}).")
                return True
            else:
                self.logger.error(
                    f"Failed to follow user '{target_login}' ({target_user_id}). "
                    f"Status code: {follow_resp.status_code}, Response: {follow_resp.text}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Exception occurred while following user '{target_login}': {e}", exc_info=True)
            return False

    def set_bot_chat_color(self, bearer_token: str, color: str = "spring_green") -> bool:
        """
        Updates the bot's username color in Twitch chat. 
        Requires 'user:manage:chat_color' scope on the bot's OAuth token.
        :param bearer_token: OAuth token for the bot account
        :param color: An allowed color name (e.g. 'green', 'spring_green') 
                    or a hex string if the bot has Turbo/Prime. 
        :return: True if the color is updated successfully, False otherwise.
        """
        # Validate color is one of Twitch's allowed constants or #hex
        allowed_colors = {
            "blue", "blue_violet", "cadet_blue", "chocolate", "coral", "dodger_blue",
            "firebrick", "golden_rod", "green", "hot_pink", "orange_red", "red",
            "sea_green", "spring_green", "yellow_green"
        }

        # If it's not a hex and not in the allowed list, fallback or log an error
        # (You might want to handle that more gracefully)
        if not (color.startswith("#") or color in allowed_colors):
            self.logger.warning(f"Color '{color}' is not an allowed color or valid hex; defaulting to 'green'.")
            color = "green"

        headers = {
            "Client-ID": self.config.twitch_bot_client_id,
            "Authorization": f"Bearer {bearer_token}"
        }

        # Build the PUT URL
        url = f"{self.TWITCH_API_BASE_URL}/chat/color?user_id={self.config.twitch_bot_user_id}&color={color}"

        self.logger.debug(f"Attempting to update bot's chat color to '{color}' using URL: {url}")
        try:
            resp = requests.put(url, headers=headers)
            if resp.status_code == 204:
                self.logger.info(f"Successfully updated bot username color to '{color}'.")
                return True
            else:
                self.logger.error(
                    f"Failed to set chat color to '{color}'. "
                    f"Status: {resp.status_code}, Response: {resp.text}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Exception while updating chat color to '{color}': {e}", exc_info=True)
            return False

    async def update_channel_viewers(self, bearer_token: str) -> list[dict]:
        """
        Fetch current viewers via the Twitch API, format them, 
        and upsert them into the in-memory queue, returning the deduplicated results.
        """
        # Step 1: Fetch data
        raw_data = await self._fetch_viewers_from_twitch(bearer_token=bearer_token)
        if not raw_data:
            self.logger.warning("No raw viewer data returned from Twitch.")
            return []

        # Step 2: Transform/Format data
        formatted_records = self._format_viewers_for_storage(raw_data)

        # Step 3: Deduplicate & enqueue
        final_queue_records = self._upsert_viewers_in_queue(formatted_records)

        return final_queue_records
    
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
    async def _fetch_viewers_from_twitch(self, bearer_token) -> dict:

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
                self.logger.warning(f'Failed to retrieve channel viewers: {response.status_code}, {response.text}')
                return None
        except Exception as e:
            self.logger.exception(f'Error fetching channel viewers: {e}')
            return None

    async def retrieve_active_usernames(self, bearer_token) -> list[str]:
        try:
            viewer_data = await self._fetch_viewers_from_twitch(bearer_token)
        except Exception as e:
            self.logger.warning(f"Failed to fetch channel viewer data: {e}")
            return None

        if not viewer_data:
            self.logger.warning("Viewer data is None or empty.")
            return None

        current_users_in_session = viewer_data.get('data', [])
        current_user_names = [user['user_login'] for user in current_users_in_session]
        self.logger.debug(f"current_user_names: {current_user_names}")
        return current_user_names

    def _format_viewers_for_storage(self, viewer_data_json) -> list[dict]:
        self.logger.debug('Processing channel viewers data')
        timestamp = utils.get_datetime_formats()['sql_format']
        
        if viewer_data_json:
            channel_viewers_list_dict = viewer_data_json.get('data', [])
            for item in channel_viewers_list_dict:
                item['timestamp'] = timestamp
            self.logger.debug(f"channel_viewers_list_dict:")
            self.logger.debug(channel_viewers_list_dict)
        else:
            self.logger.error("Invalid viewer data provided to _format_viewers_for_storage")
            raise ValueError("Invalid viewer data provided to _format_viewers_for_storage")
        
        return channel_viewers_list_dict

    async def _upsert_viewers_in_queue(self, records: list[dict]) -> None:

        self.logger.debug(f'Enqueuing {len(records)} records to channel_viewers_queue')

        # Initialize the queue if it doesn't exist
        if not hasattr(self, 'channel_viewers_queue') or self.channel_viewers_queue is None:
            self.channel_viewers_queue = []
            self.logger.debug(f'channel_viewers_queue initialized: {self.channel_viewers_queue}')
            
        if hasattr(self, 'channel_viewers_queue') and self.channel_viewers_queue is not None:
            self.logger.debug(f'channel_viewers_queue has {len(self.channel_viewers_queue)} rows')

        # Extend the existing queue with new records
        self.channel_viewers_queue.extend(records)

        df = pd.DataFrame(self.channel_viewers_queue)
        df = df.sort_values(['user_id', 'timestamp']).drop_duplicates(subset='user_id', keep='last')

        # Update the queue and log
        self.channel_viewers_queue = df.to_dict('records')
        self.logger.debug(f'channel_viewers_queue updated with {len(self.channel_viewers_queue)} rows')

if __name__ == "__main__":
    twitch_api = TwitchAPI()
    twitch_api.logger.info('TwitchAPI initialized.')
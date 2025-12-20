from tenacity import retry, stop_after_attempt, wait_fixed
import requests
import pandas as pd
import os
import asyncio

from classes.ConfigManagerClass import ConfigManager

from my_modules import my_logging
from my_modules import utils

# Twitch API Endpoints
TWITCH_API_BASE_URL = "https://api.twitch.tv/helix"
USERS_ENDPOINT = "/users"
MODERATORS_ENDPOINT = "/moderation/moderators"
CHATTERS_ENDPOINT = "/chat/chatters"

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

        # Lock to protect the channel_viewers_queue from concurrent access
        self._channel_viewers_queue_lock = asyncio.Lock()

        self.channel_viewers_queue = []

        try:
            self.config.twitch_bot_user_id = self._fetch_user_id(
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
            self.config.twitch_broadcaster_user_id = self._fetch_user_id(
                #bearer_token=self.config.twitch_bot_access_token,
                bearer_token=os.getenv("TWITCH_BOT_ACCESS_TOKEN"),
                login_name=self.config.twitch_bot_channel_name
                )
            self.logger.debug(f"Broadcasters User ID: {self.config.twitch_broadcaster_user_id}")    
        except Exception as e:
            self.logger.error(f"Failed to retrieve broadcaster's user ID: {e}")
            self.config.twitch_broadcaster_user_id = None

    def _fetch_user_id(self, bearer_token, login_name):
        self.logger.debug(f"Getting bot's user ID using token...")

        # Twitch API authentication headers
        HEADERS = {
            "Client-ID": self.config.twitch_bot_client_id,
            "Authorization": f'Bearer {bearer_token}'
        }

        # Get the user ID of the bot
        url = f"{TWITCH_API_BASE_URL}{USERS_ENDPOINT}?login={login_name}"
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

    #     url = f"{TWITCH_API_BASE_URL}{MODERATORS_ENDPOINT}"
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
        url_get_user = f"{TWITCH_API_BASE_URL}{USERS_ENDPOINT}?login={target_login}"
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
        url_follow = f"{TWITCH_API_BASE_URL}/users/follows"
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
        url = f"{TWITCH_API_BASE_URL}/chat/color?user_id={self.config.twitch_bot_user_id}&color={color}"

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

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
    async def _fetch_viewers_from_twitch(self, bearer_token) -> list:
        """Fetch all pages of viewers and return them as a simple list."""

        try:
            chatters_endpoint_url = f"{TWITCH_API_BASE_URL}{CHATTERS_ENDPOINT}"
            params = {
                'broadcaster_id': self.config.twitch_broadcaster_user_id,
                'moderator_id': self.config.twitch_bot_user_id
            }
            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'Client-Id': self.config.twitch_bot_client_id
            }

            all_viewers_data = []
            while True:
                response = requests.get(chatters_endpoint_url, params=params, headers=headers)
                if response.status_code != 200:
                    self.logger.warning(
                        f'Failed to retrieve channel viewers: {response.status_code}, {response.text}'
                    )
                    return None

                # Grab data from this page
                json_data = response.json()
                page_data = json_data.get('data', [])
                self.logger.info(f"Page data: {page_data}")
                all_viewers_data.extend(page_data)

                # Check for next page
                pagination = json_data.get('pagination', {})
                cursor = pagination.get('cursor')
                if cursor:
                    params['after'] = cursor
                else:
                    # No more pages left
                    break

            self.logger.info(f"Successfully fetched {len(all_viewers_data)} total viewers.")
            return all_viewers_data

        except Exception as e:
            self.logger.exception(f"Error fetching channel viewers: {e}")
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

        current_users_in_session = viewer_data
        current_user_names = [user['user_login'] for user in current_users_in_session]
        self.logger.info(f"current_user_names: {current_user_names}")
        return current_user_names

    def _prepare_viewers_for_queue(self, channel_viewers_list: list) -> list[dict]:
        self.logger.info('Processing channel viewers data')
        timestamp = utils.get_current_datetime_formatted()['sql_format']
        
        if channel_viewers_list:
            for item in channel_viewers_list:
                item['timestamp'] = timestamp
            self.logger.debug(f"channel_viewers_list_dict:")
            self.logger.debug(channel_viewers_list)
        else:
            self.logger.error("Invalid viewer data provided to _prepare_viewers_for_queue")
            raise ValueError("Invalid viewer data provided to _prepare_viewers_for_queue")
        
        self.logger.debug(f"Prepared channel viewers queue.  Now contains {len(self.channel_viewers_queue)} records.")
        return channel_viewers_list

    async def update_channel_viewers_queue(self, bearer_token: str) -> list[dict]:
        """
        Fetch current viewers via the Twitch API, format them, 
        and upsert them into the in-memory queue, returning the deduplicated results.
        """
        # Step 1: Fetch data
        channel_viewers_list = await self._fetch_viewers_from_twitch(bearer_token=bearer_token)
        if not channel_viewers_list:
            self.logger.warning("No raw viewer data returned from Twitch.")
            return []

        # Step 2: Transform/Format data, deduplicate & enqueue
        prepared_channel_viewers_list = self._prepare_viewers_for_queue(channel_viewers_list)
        await self._merge_channel_viewers_queue(prepared_channel_viewers_list)

        self.logger.info(f"Updated channel viewers queue.  Now contains {len(self.channel_viewers_queue)} records.")
    
    async def _merge_channel_viewers_queue(self, records: list[dict]) -> None:
        """
        Deduplicate new viewer records with existing ones and update the in-memory queue.
        Protected by an asyncio Lock to avoid concurrency issues.
        """
        # Acquire the lock before modifying the shared queue
        async with self._channel_viewers_queue_lock:
            self.logger.debug(f'Enqueuing {len(records)} records to channel_viewers_queue')

            # Ensure queue exists
            if self.channel_viewers_queue is None:
                self.channel_viewers_queue = []

            # Create a dictionary to track the latest record per user_id
            latest_records = {
                record['user_id']: record 
                for record in (self.channel_viewers_queue + records)
            }

            # Sort by timestamp and keep only the latest entry per user_id
            self.channel_viewers_queue = sorted(latest_records.values(), key=lambda x: x['timestamp'])

            if len(self.channel_viewers_queue) < 1:
                self.logger.warning(
                    "Channel viewers queue is empty, this should not happen.  Bot User should always show up in this list."
                )
            else:
                self.logger.debug(f"Merged channel viewers queue.  Now contains {len(self.channel_viewers_queue)} records.")

if __name__ == "__main__":
    twitch_api = TwitchAPI()
    twitch_api.logger.info('TwitchAPI initialized.')
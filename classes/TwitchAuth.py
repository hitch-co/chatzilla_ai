import os
import requests
import uuid
import json
import time
from urllib.parse import urlencode

from my_modules.my_logging import create_logger

#NOTE: auth code grant flow
class TwitchAuth:
    def __init__(self, config):
        self.config = config
        self.logger = create_logger(
            dirname='log', 
            logger_name='TwitchAuth', 
            debug_level='INFO', 
            mode='w',
            stream_logs = True,
            encoding='UTF-8'
            )
        self.access_token_expiry = None

    def get_auth_url(self):
        params = {
            'response_type': 'code',
            'client_id': self.config.twitch_bot_client_id,
            'redirect_uri': f'http://localhost:{self.config.chatzilla_port_number}/{self.config.twitch_bot_redirect_path}',
            'scope': self.config.twitch_bot_scope,
            'state': uuid.uuid4().hex
        }
        self.logger.debug(f"Params for Twitch auth URL: {params}")
        url = f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"
        self.logger.debug(f"Generated Twitch auth URL: {url}")
        return url

    def get_response_object(self, code):
        data = {
            'client_id': self.config.twitch_bot_client_id,
            'client_secret': self.config.twitch_bot_client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': f'http://localhost:{self.config.chatzilla_port_number}/{self.config.twitch_bot_redirect_path}'
        }
        self.logger.debug(f"Data for POST request to Twitch: {data}")
        try:
            response = requests.post('https://id.twitch.tv/oauth2/token', data=data)
            self.logger.debug(f"Response from Twitch: {response}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error: {e}")
            return None
        return response

    async def refresh_access_token(self):
        data = {
            'client_id': self.config.twitch_bot_client_id,
            'client_secret': self.config.twitch_bot_client_secret,
            'refresh_token': os.environ["TWITCH_BOT_REFRESH_TOKEN"],
            'grant_type': 'refresh_token'
        }
        response = requests.post('https://id.twitch.tv/oauth2/token', data=data)
        return response
    
    def handle_auth_callback(self, response):
        self.logger.debug(f"This is the response from Twitch (status code: {response.status_code}):")
        self.logger.debug(json.dumps(response.json(), indent=4))
        
        if response.status_code == 200:
            response_json = response.json()
            access_token = response_json['access_token']
            refresh_token = response_json['refresh_token']        
            os.environ["TWITCH_BOT_ACCESS_TOKEN"] = access_token
            os.environ["TWITCH_BOT_REFRESH_TOKEN"] = refresh_token
            self.config.twitch_bot_access_token = access_token
            self.config.twitch_bot_refresh_token = refresh_token

            # Create expiration time for access token (expirs_in is in seconds)
            self.access_token_expiry = time.time() + int(response_json['expires_in'])
            
            return True, "Authentication successful. Bot is starting."
        else:
            self.logger.error(f"Error: Response from Twitch was {response.status_code}")
            return False, f"Authentication failed. {response.json()}"
        


        
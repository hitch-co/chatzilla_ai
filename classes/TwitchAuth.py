import os
import requests
import uuid
import json
import time
from urllib.parse import urlencode

from my_modules.my_logging import create_logger

from classes.ConfigManagerClass import ConfigManager

class TwitchAuth:
    def __init__(self, config):
        self.config = config
        self.logger = create_logger(
            dirname='log', 
            logger_name='TwitchAuth', 
            debug_level='INFO', 
            mode='w',
            stream_logs = False,
            encoding='UTF-8'
            )
        self.access_token_expiry = None
        config = ConfigManager.get_instance()

    def get_auth_url(self):
        params = {
            'response_type': 'code',
            'client_id': self.config.twitch_bot_client_id,
            'redirect_uri': f'http://localhost:{self.config.input_port_number}/{self.config.twitch_bot_redirect_path}',
            'scope': self.config.twitch_bot_scope,
            'state': uuid.uuid4().hex
        }
        url = f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"
        self.logger.debug(f"Generated Twitch auth URL: {url}")
        return url

    def get_response_object(self, code):
        data = {
            'client_id': self.config.twitch_bot_client_id,
            'client_secret': self.config.twitch_bot_client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': f'http://localhost:{self.config.input_port_number}/{self.config.twitch_bot_redirect_path}'
        }
        response = requests.post('https://id.twitch.tv/oauth2/token', data=data)
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
        self.logger.debug("This is the response from Twitch.  Dump it")
        self.logger.debug(json.dumps(response.json(), indent=4))
        
        if response.status_code == 200:
            tokens = response.json()
            os.environ["TWITCH_BOT_ACCESS_TOKEN"] = tokens['access_token']
            os.environ["TWITCH_BOT_REFRESH_TOKEN"] = tokens['refresh_token']

            # Create expiration time for access token (expirs_in is in seconds)
            self.access_token_expiry = time.time() + int(tokens['expires_in'])
            
            return True, "Authentication successful. Bot is starting."
        else:
            self.logger.error("Failed to retrieve tokens from Twitch.")
            return False, "Authentication failed."
        


        
import os
import requests
import uuid
import json
from urllib.parse import urlencode

class TwitchAuth:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def get_auth_url(self):
        params = {
            'response_type': 'code',
            'client_id': self.config.twitch_bot_client_id,
            'redirect_uri': f'http://localhost:{self.config.input_port_number}/{self.config.twitch_bot_redirect_path}',
            'scope': self.config.twitch_bot_scope,
            'state': uuid.uuid4().hex
        }
        url = f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"
        self.logger.info(f"Generated Twitch auth URL: {url}")
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

    def handle_auth_callback(self, response):
        self.logger.debug("This is the response from Twitch.  Dump it")
        self.logger.debug(json.dumps(response.json(), indent=4))
        
        if response.status_code == 200:
            tokens = response.json()
            os.environ["TWITCH_BOT_ACCESS_TOKEN"] = tokens['access_token']
            os.environ["TWITCH_BOT_REFRESH_TOKEN"] = tokens['refresh_token']
            return True, "Authentication successful. Bot is starting."
        else:
            self.logger.error("Failed to retrieve tokens from Twitch.")
            return False, "Authentication failed."
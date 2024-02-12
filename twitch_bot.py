import uuid
import requests
import os
import asyncio
from threading import Thread
from flask import Flask, request

from classes.ConfigManagerClass import ConfigManager
ConfigManager.initialize(yaml_filepath=r'C:\Users\Admin\OneDrive\Desktop\_work\__repos (unpublished)\_____CONFIG\chatzilla_ai\config\config.yaml')

from classes.TwitchBotClass import Bot
from config.DependencyInjector import DependencyInjector

from my_modules.my_logging import create_logger

use_reloader_bool = False
runtime_logger_level = 'DEBUG'
root_logger = create_logger(
    dirname='log',
    logger_name='_logger_root_twitch_bot',
    debug_level=runtime_logger_level,
    mode='w'
)

# Bot Thread
TWITCH_CHATFORME_BOT_THREAD = None

# Grab the config
config = ConfigManager.get_instance()

config.input_port_number = str(config.input_port_number)
twitch_bot_redirect_path = config.twitch_bot_redirect_path
TWITCH_BOT_CLIENT_ID = config.twitch_bot_client_id
TWITCH_BOT_CLIENT_SECRET = config.twitch_bot_client_secret
TWITCH_BOT_SCOPE = config.twitch_bot_scope

# Initialize Flask app
app = Flask(__name__)

#App route home
@app.route('/')
def hello_world():
    return "Hello, you're probably looking for the /auth page!"

#app route auth
@app.route('/auth')
def auth():
    base_url_auth = 'https://id.twitch.tv/oauth2/authorize'
    redirect_uri = f'http://localhost:{config.input_port_number}/{twitch_bot_redirect_path}'
    params_auth = f'?response_type=code&client_id={TWITCH_BOT_CLIENT_ID}&redirect_uri={redirect_uri}&scope={TWITCH_BOT_SCOPE}&state={uuid.uuid4().hex}'
    url = base_url_auth+params_auth
    root_logger.info(f"Generated redirect_uri: {redirect_uri}")
    return f'<a href="{url}">Connect with Twitch</a>'

#app route auth callback
@app.route('/callback')
def callback():
    global TWITCH_CHATFORME_BOT_THREAD  # declare the variable as global inside the function
   
    # Runtime args
    redirect_uri = f'http://localhost:{config.input_port_number}/{twitch_bot_redirect_path}'
    
    # Args in response
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        return f"Error: {error}"
    
    data = {
        'client_id': TWITCH_BOT_CLIENT_ID,
        'client_secret': TWITCH_BOT_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }  
    response = requests.post('https://id.twitch.tv/oauth2/token', data=data)
    
    if response.status_code == 200:
        #capture tokens
        TWITCH_BOT_ACCESS_TOKEN = response.json()['access_token']
        TWITCH_BOT_REFRESH_TOKEN = response.json()['refresh_token']

        #add the access/refresh token to the environments
        os.environ["TWITCH_BOT_ACCESS_TOKEN"] = TWITCH_BOT_ACCESS_TOKEN        
        os.environ["TWITCH_BOT_REFRESH_TOKEN"] = TWITCH_BOT_REFRESH_TOKEN

        # Only start bot thread if it's not already running
        if TWITCH_CHATFORME_BOT_THREAD is None or not TWITCH_CHATFORME_BOT_THREAD.is_alive():
            TWITCH_CHATFORME_BOT_THREAD = Thread(target=run_bot, args=(TWITCH_BOT_ACCESS_TOKEN, config))
            TWITCH_CHATFORME_BOT_THREAD.start()
            twitch_bot_status = 'Twitch bot was not active or did not exist and thread was started.'
        else: 
            twitch_bot_status = 'Twitch bot was active so the existing bot thread was left active.'

        return f'<a>{twitch_bot_status} Access Token and Refresh Token have been captured and set in the current environment</a>'
    else:
        return '<a>There was an issue retrieving and setting the access token.  If you would like to include more detail in this message, return "template.html" or equivalent using the render_template() method from flask and add it to this response...'

#This is run after the auth process completes
def run_bot(TWITCH_BOT_ACCESS_TOKEN, config):

    #asyncio event loop
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    
    #dependency injector
    dependencies = DependencyInjector(config = config)
    dependencies.create_dependencies()

    #instantiate the class
    bot = Bot(
        TWITCH_BOT_ACCESS_TOKEN, 
        config=config,
        gpt_client=dependencies.gpt_client,
        bq_uploader=dependencies.bq_uploader,
        tts_client=dependencies.tts_client,
        message_handler=dependencies.message_handler
        )
    bot.run()

#NOTE: When /callback is hit, new bot instance is started.   
if __name__ == "__main__":
    app.run(
        port=config.input_port_number, 
        debug=True, 
        use_reloader=use_reloader_bool
        )
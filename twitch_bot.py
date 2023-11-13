# Import required modules
import asyncio
from threading import Thread
from flask import Flask, request
import uuid
import requests
import os
from my_modules.my_logging import create_logger
from my_modules.config import load_yaml, load_env
from classes.TwitchBotClass import Bot
from classes.ArgsConfigManagerClass import ArgsConfigManager

# Configuration
use_reloader_bool = False
runtime_logger_level = 'DEBUG'

# Initialize the root logger
root_logger = create_logger(
    dirname='log',
    logger_name='_logger_root_twitch_bot',
    debug_level=runtime_logger_level,
    mode='a'
)
root_logger.info("----- This is the start of an app start root log! -----")

# Global Variables
TWITCH_CHATFORME_BOT_THREAD = None

# Load configurations from YAML and environment variables
yaml_data = load_yaml(yaml_dirname='config', yaml_filename='config.yaml')
load_env(env_dirname=yaml_data['env_dirname'], env_filename=yaml_data['env_filename'])
twitch_bot_redirect_path = yaml_data['twitch-app']['twitch_bot_redirect_path']
TWITCH_BOT_CLIENT_ID = os.getenv('TWITCH_BOT_CLIENT_ID')
TWITCH_BOT_CLIENT_SECRET = os.getenv('TWITCH_BOT_CLIENT_SECRET')
TWITCH_BOT_SCOPE = os.getenv('TWITCH_BOT_SCOPE')

# Initialize Flask app
app = Flask(__name__)
args_config = ArgsConfigManager()

#App route home
@app.route('/')
def hello_world():
    return "Hello, you're probably looking for the /auth page!"

#app route auth
@app.route('/auth')
def auth():
    base_url_auth = 'https://id.twitch.tv/oauth2/authorize'
    input_port_number = str(args_config.input_port_number)
    redirect_uri = f'http://localhost:{input_port_number}/{twitch_bot_redirect_path}'
    params_auth = f'?response_type=code&client_id={TWITCH_BOT_CLIENT_ID}&redirect_uri={redirect_uri}&scope={TWITCH_BOT_SCOPE}&state={uuid.uuid4().hex}'
    url = base_url_auth+params_auth
    print(f"Generated redirect_uri: {redirect_uri}")
    return f'<a href="{url}">Connect with Twitch</a>'

#app route auth callback
@app.route('/callback')
def callback():
    global TWITCH_CHATFORME_BOT_THREAD  # declare the variable as global inside the function

    # Runtime args
    input_port_number = str(args_config.input_port_number)
    redirect_uri = f'http://localhost:{input_port_number}/{twitch_bot_redirect_path}'
    
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
            TWITCH_CHATFORME_BOT_THREAD = Thread(target=run_bot, args=(TWITCH_BOT_ACCESS_TOKEN,))
            TWITCH_CHATFORME_BOT_THREAD.start()
            twitch_bot_status = 'Twitch bot was not active or did not exist and thread was started.'
        else: 
            twitch_bot_status = 'Twitch bot was active so the existing bot thread was left active.'

        return f'<a>{twitch_bot_status} Access Token and Refresh Token have been captured and set in the current environment</a>'
    else:
        # output = {}
        # output['response.text'] = response.json()
        return '<a>There was an issue retrieving and setting the access token.  If you would like to include more detail in this message, return "template.html" or equivalent using the render_template() method from flask and add it to this response...'

#This is run immediately after the authentication process.
def run_bot(TWITCH_BOT_ACCESS_TOKEN):

    #load yaml_data for init'ing Bot class
    yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname='config')
    
    #TODO could be moved to a ConfigManager(). Only needs a handful of configuration parameters
    load_env(env_filename=yaml_data['env_filename'], env_dirname=yaml_data['env_dirname'])

    #asyncio event loop
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    
    #instantiate the class
    bot = Bot(
        TWITCH_BOT_ACCESS_TOKEN, 
        yaml_data=yaml_data
        )
    bot.run()

#TODO/NOTE: Everytime /callback is hit, a new bot instance is being started.   
# This could cause problems
if __name__ == "__main__":
    app.run(port=args_config.input_port_number, debug=True, use_reloader=use_reloader_bool)
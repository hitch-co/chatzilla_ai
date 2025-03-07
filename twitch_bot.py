import os

from classes.ConfigManagerClass import ConfigManager
from flask import Flask, redirect, request, url_for

from classes.TwitchAuth import TwitchAuth
from classes.TwitchBotManager import TwitchBotManager
from my_modules.my_logging import create_logger

use_reloader_bool = False
runtime_logger_level = 'INFO'

# Initialize the Flask application
app = Flask(__name__)

# Load configuration
yaml_filepath = os.getenv('CHATZILLA_CONFIG_YAML_FILEPATH')
ConfigManager.initialize(yaml_filepath=yaml_filepath)
config = ConfigManager.get_instance()

# Setup logger
logger = create_logger(
    dirname='log',
    logger_name='twitch_bot.py',
    debug_level=runtime_logger_level,
    mode='w'
)

# Twitch bot manager
twitch_bot_manager = TwitchBotManager(config, logger)

# Twitch authentication helper
twitch_auth = TwitchAuth(config=config)

@app.route('/')
def index():
    return "Hello, you're probably looking for the /auth page!"

@app.route('/auth')
def auth():
    return redirect(twitch_auth.get_auth_url())

@app.route('/callback')
def callback():
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        logger.error(f"Error during authentication: {error}")
        return "Error during authentication."

    # Exchange code for tokens and start bot thread
    response = twitch_auth.get_response_object(code)
    logger.debug(f"Response from Twitch: {response}")

    success, message = twitch_auth.handle_auth_callback(response)

    if success:
        twitch_bot_manager.start_bot(twitch_auth)
    return message

if __name__ == "__main__":
    app.run(port=config.chatzilla_port_number, debug=True, use_reloader=use_reloader_bool)
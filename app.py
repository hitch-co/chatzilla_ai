from flask import Flask, redirect, request, url_for
from classes.TwitchAuth import TwitchAuth
from classes.BotThread import start_bot_thread
import classes.BotThread
from classes.ConfigManagerClass import ConfigManager
from my_modules.my_logging import create_logger

use_reloader_bool = False
runtime_logger_level = 'DEBUG'

# Initialize the Flask application
app = Flask(__name__)

# Load configuration
ConfigManager.initialize(yaml_filepath=r'C:\Users\Admin\OneDrive\Desktop\_work\__repos (unpublished)\_____CONFIG\chatzilla_ai\config\config.yaml')
config = ConfigManager.get_instance()

# Setup logger
logger = create_logger(
    dirname='log',
    logger_name='_logger_root_app',
    debug_level=runtime_logger_level,
    mode='w'
)

# Twitch authentication helper
twitch_auth = TwitchAuth(config=config, logger=logger)

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
    success, message = twitch_auth.handle_auth_callback(code)
    if success:
        start_bot_thread(config, logger)
    return message

if __name__ == "__main__":
    app.run(port=config.input_port_number, debug=True, use_reloader=use_reloader_bool)
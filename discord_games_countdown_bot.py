#.py
"""
Discord-Flask Bot
=================

This script runs a Flask server and a Discord bot simultaneously. It uses the Flask framework to provide a web API, and the discord.py library to interact with Discord. The Flask server exposes an endpoint `/send_games_command`, which triggers a Discord bot to send a specific message to a given Discord channel.

Before Running the Script
-------------------------
1. Create a `config.env.template` and `config.yaml.template` in the appropriate directory.
2. Rename `config.env.template` to `config.env` and `config.yaml.template` to `config.yaml`.
3. Update the `config.env` file with necessary environment variables.
4. Update the `config.yaml` file with necessary configurations.

Dependencies
------------
- Flask
- discord.py
- threading
- asyncio
- logging
- os
- Custom modules for loading YAML and environment variables (`load_yaml`, `load_env`)

Functions
---------
- on_ready(): Discord bot event that triggers when the bot logs in.
- send_games_command(number_of_minutes=15): Flask route to send a command to a Discord channel.
- run_flask(): Function to start the Flask app.
- run_discord(): Coroutine to start the Discord bot.

Flask Routes
------------
- `/send_games_command` : Sends a Discord message to a specific channel indicating a user is available for games.

Environment Variables
----------------------
- `DISCORD_BOT_PLAY_GAMES_IN_BOT_TOKEN` : Discord bot token.

YAML Configurations
-------------------
- `server_guild_id` : Discord server ID.
- `server_channel_id` : Discord channel ID.
- `discord_games_countdown_username` : Discord username for countdown.
- `env_filename` : Name of the environment file.
- `env_dirname` : Directory where the environment file is located.

Author
------
Eric Hitchman, with the assistance of GPT4

"""
from my_modules.config import load_yaml, load_env
from my_modules.utils import shutdown_server

import discord
from flask import Flask, request, jsonify

import threading
import asyncio

import logging
import os
import sys
import time

#############################
#set yaml params
yaml_filename = 'config-games-in.yaml'
yaml_dirname = 'config'
#############################

# Initialize the app and client
app = Flask(__name__)
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load yaml file
yaml_data = load_yaml(yaml_filename=yaml_filename, yaml_dirname=yaml_dirname)
env_filename = yaml_data['env_filename']
env_dirname = yaml_data['env_dirname']

# Load environment variables
load_env(env_filename=env_filename, env_dirname=env_dirname)

#Load params from env/config.yaml
server_guild_id = int(yaml_data['server_guild_id']) #TODO: update to take from environment variable
server_channel_id = int(yaml_data['server_channel_id']) #TODO: update to take from environment variable
discord_games_countdown_username = yaml_data['discord_games_countdown_username']
discord_games_countdown_default_minutes = yaml_data['discord_games_countdown_default_minutes']
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_PLAY_GAMES_IN_BOT_TOKEN')

#########################
# On ready
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

#########################
# Flask route (use app.route('/route',['POST']) iuw but include payload in .bat file or elsewhere )
@app.route('/send_games_command')
def send_games_command():
    # Use the below if you decide to grab user data from the payload sent  to /send_games_command
    # discord_games_countdown_username = request.json.get('DISCORD_GAMES_COUNTDOWN_USERNAME')

    # Retrieve the number_of_minutes from the query parameters. Use the default value if not provided.
    number_of_minutes = request.args.get('number_of_minutes', default=discord_games_countdown_default_minutes, type=int)
    print(f"DEBUG: Retrieved number_of_minutes: {number_of_minutes}")

    if not discord_games_countdown_username:
            return jsonify({'status':'failure', 'message':'You haven"t updated your custom username'})
    guild = client.get_guild(server_guild_id)
    if guild:
        channel = guild.get_channel(server_channel_id)
        if channel:
            asyncio.run_coroutine_threadsafe(channel.send(f'{discord_games_countdown_username} is @here and available in {str(number_of_minutes)} minutes for some games.  Hit "dem up!'), loop)
            jsonify({"status": "failure", "message": "Mission complete!"})            
            
            #Unsure if working
            time.sleep(4)
            shutdown_server()
            sys.exit()
            
    #will only be reached if no guild/channel is set/found
    return jsonify({"status": "failure", "message": "Guild or channel not found"})



#########################
# Function to run Flask
def run_flask():
    app.run(port=5000)

#########################
# Function to run the Discord client
async def run_discord():
    await client.start(DISCORD_BOT_TOKEN)

#########################
# Create a new loop for discord
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

#########################
# Run Flask in its own thread
flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# Run Discord client in the main thread
loop.run_until_complete(run_discord())
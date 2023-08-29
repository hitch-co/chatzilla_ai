from flask import Flask, request, jsonify
import discord
import logging
from modules import load_yaml, load_env
import os
import threading
import asyncio

# Initialize the app and client
app = Flask(__name__)
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load yaml file
yaml_data = load_yaml(yaml_filename='config.yaml', yaml_dirname="C:\\_repos\\chatforme_bots\\config")
server_guild_id = int(yaml_data['server_guild_id']) #TODO: update to take from environment variable
server_channel_id = int(yaml_data['server_channel_id']) #TODO: update to take from environment variable
discord_games_countdown_username = yaml_data['discord_games_countdown_username']


# Load environment variables
load_env(env_filename=yaml_data['env_filename'], env_dirname=yaml_data['env_dirname'])
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_PLAY_GAMES_IN_BOT_TOKEN')

# On ready
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

# Flask route (use app.route('/route',['POST']) iuw but include payload in .bat file or elsewhere )
@app.route('/send_games_command')
def send_games_command(number_of_minutes = 15):
    # Use the below if you decide to grab user data from the payload sent  to /send_games_command
    # discord_games_countdown_username = request.json.get('DISCORD_GAMES_COUNTDOWN_USERNAME')

    discord_games_countdown_username = yaml_data['discord_games_countdown_username']

    if not discord_games_countdown_username:
            return jsonify({'status':'failure', 'message':'You haven"t updated your custom username'})
    guild = client.get_guild(server_guild_id)
    if guild:
        channel = guild.get_channel(server_channel_id)
        if channel:
            asyncio.run_coroutine_threadsafe(channel.send(f'{discord_games_countdown_username} is @here and available in {str(number_of_minutes)} minutes for some games.  Hit "dem up!'), loop)
            return jsonify({"status": "success", "message": "Command sent"})
    return jsonify({"status": "failure", "message": "Guild or channel not found"})

# Function to run Flask
def run_flask():
    app.run(port=5000)

# Function to run the Discord client
async def run_discord():
    await client.start(DISCORD_BOT_TOKEN)

# Create a new loop for discord
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Run Flask in its own thread
flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# Run Discord client in the main thread
loop.run_until_complete(run_discord())
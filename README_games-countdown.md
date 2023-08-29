# Discord-Flask Bot Documentation

## Introduction

This documentation covers a bot script that runs both a Flask server and a Discord bot. The Flask server exposes an endpoint `/send_games_command` that triggers a specific action in a Discord channel. The Discord bot is set up using the `discord.py` library, and Flask is used for the web API.

---

## Configuration

### Environment File (`config.env`)

1. Rename `config.env.template` to `config.env`.
2. Populate it with the relevant keys and tokens. For example:

```env
OPENAI_API_KEY='sk-xxxxx'
DISCORD_BOT_KEY='xxxxx'
DISCORD_BOT_PLAY_GAMES_IN_BOT_TOKEN='xxxxx'
```

### YAML Configuration File (`config.yaml`)

1. Rename `config.yaml.template` to `config.yaml`.
2. Update the YAML file with the relevant settings. Only the ones used in the Python script are documented here.

```yaml
env_filename: 'config.env'
env_dirname: 'C:\\_repos\\chatforme_bots\\config'
server_guild_id: '1110236483505377400'
server_channel_id: '1145905547946762252'
discord_games_countdown_username: 'yo daddy'
```

---

## Python Bot Script (`games_countdown_bot.py`)

This is the main Python file that houses both the Flask application and Discord bot client. It utilizes threading to run both Flask and the Discord bot.

- **Flask Routes**:  
  - `/send_games_command`: Sends a countdown message to a specific Discord channel.
  
- **Environment Variables Loaded**:  
  - `DISCORD_BOT_PLAY_GAMES_IN_BOT_TOKEN`: The Discord Bot token.

For more details, you can refer to the Python script itself.

---

## Batch File (`games_countdown.bat`)

The batch file is used to automate the startup process and triggering of the Flask endpoint. Here is what it does:

1. Optionally prompts the user for a custom Discord username.
2. Starts the Flask app.
3. Makes a GET request to the Flask route `/send_games_command`.

```bat
@echo off
::startup the flask app
start python C:/_repos/chatforme_bots/games_countdown_bot.py
::Wait
ping localhost -n 3 > nul
::Visit the app route to execute the games countdown command
curl -X GET -H "Content-Type: application/json" http://localhost:5000/send_games_command
```

---

## How to Run

1. Make sure the `config.env` and `config.yaml` files are properly configured.
2. Run the `games_countdown.bat` file to start the Flask application and Discord bot.

---

## Dependencies

- Flask
- discord.py
- threading
- asyncio
- logging
- os

---

## Author

Eric Hitchman, with the assistance of GPT4

---

For any additional information or queries, feel free to contact the author.

Feel free to modify this `.md` file according to your requirements.

# eh-bot-chatforme
 
# Discord-Twitch Chatbot

This project contains a Discord and Twitch bot that uses OpenAI's GPT-4 to generate automated responses.

# Installation

Make sure to install ffmpeg for anything related to voice activity.  Once you've installed ffmpeg remember to either add the ffmpeg/ffplay/ffprobe exes to either the $PATH or add them directly to the repo top-level directory

## Configuration

The main configuration parameters for the bot are stored in the `config.yaml` file, which is located in the `config` directory. The parameters are as follows:

- `env_filename`: The name of the file that contains the environment variables.
- `env_dirname`: The directory where the `env_filename` is located.
- `msg_history_limit`: The maximum number of previous messages that the bot should consider when generating a response.
- `num_bot_responses`: The number of bot responses to generate for each input.
- `automated_message_seconds`: The delay (in seconds) between automated messages.
- `automated_message_wordcount`: The maximum word count for automated messages.
- `chatgpt_prompt_prefix` and `chatgpt_prompt_suffix`: Prefix and suffix to be added to the input prompt when generating responses.
- `chatgpt_settings`: Default prompts for different modes.
- `chatgpt_automated_prompts` and `chatgpt_chatforme_prompts`: Predefined prompts for different contexts.

## Modules

The `modules.py` file contains the core functions for the bot:

- `openai_gpt_chatcompletion`: This function generates a response from GPT-4 given a list of previous messages.
- `load_yaml`: This function loads the configuration parameters from the `config.yaml` file.
- `load_env`: This function loads the environment variables from the `.env` file.
- `get_models`: This function retrieves the available models from the OpenAI API.

## Bot Scripts

There are two main bot scripts:

### Twitch Bot

The Twitch bot is implemented in the `twitch_bot.py` script. Here is a brief rundown of its main components and functionalities:

- The `Bot` class inherits from the `twitch_commands.Bot` class and contains all the logic for interacting with the Twitch API and OpenAI's GPT-4. It stores all recent messages in a list, and it can generate and send automated messages periodically.
- The `event_ready` method is called when the bot successfully connects to the Twitch channel. It sends a greeting message and starts a background task for sending automated messages.
- The `ouat_storyteller` method generates and sends a message every `automated_message_seconds` seconds. It fetches the prompts from the `config.yaml` file and uses GPT-4 to generate the message content.
- The `event_message` method is called whenever a new message is sent in the Twitch channel. It adds the message to the history (excluding messages sent by the bot itself or command messages), and then it passes the message to the command handler.
- The `chatforme` command generates a response from GPT-4 based on the recent message history and the current prompt.
- The `/auth` and `/callback` routes handle the OAuth2 flow for the Twitch API.

The bot starts a new instance whenever the `/callback` route is hit. This is something to be aware of if you're using the bot in a production environment.

### Discord Bot

The Discord bot is implemented in the `bot.py` script. Here is a brief rundown of its main components and functionalities:

- The `bot` instance is created using the `commands.Bot` class from the `discord.py` library. It is initialized with the bot's command prefix and the necessary Discord intents.
- The `on_ready` event is triggered when the bot successfully connects to the Discord server. It sends a console log to indicate that it's up and running.
- The `chatforme` command generates a response from GPT-4 based on the recent message history and the current prompt. The message history excludes messages sent by the bot itself and command messages. The command has several optional parameters for customizing its behavior, such as `skip_response`, `msg_history_limit`, `num_bot_responses`, `chatgpt_prompt_prefix`, and `chatgpt_prompt_suffix`.
- The `bye` command is a placeholder command that simply sends a goodbye message.

To run the Discord bot, you just need to call the `run` method on the `bot` instance with your bot's token.



## How to Run

1. Configure the `config.yaml` and `.env` files with your settings and API keys.
2. Run the `twitch_bot.py` or `bot.py` script to start the corresponding bot.

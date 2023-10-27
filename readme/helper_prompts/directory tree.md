I've got a twitch bot built out that hodls a structure that looks like this.  I've got several questions about building out a new feature that captures chat history via a function inside of my_modules/twitchio_helpers.py and then stores it inside a GCP database type structure including two primary tables, a users table and a user_interactions table.  

Im trying to determine how I should build this into the existing structure, knowing that it has some features I'd like to incorporate:

C:.
│   .gitignore
│   twitch_bot.py
│   twitch_bot_start.bat
│   
├───.vscode
│       launch.json
│
├───classes
│   │   ArticleGeneratorClass.py
│   │   ConsoleColoursClass.py
│   │   CustomExceptions.py
│   │   ChatUploaderClass.py
│   │   __init__.py
│   │
│   └───__pycache__
│           ArticleGeneratorClass.cpython-311.pyc
│           ConsoleColoursClass.cpython-311.pyc
│           CustomExceptions.cpython-311.pyc
│           __init__.cpython-311.pyc
│
├───config
│       config-games-in.env
│       config-games-in.yaml
│       config.env
│       config.env.template
│       config.yaml
│       config.yaml.template
│       disallowed_terms.json
│       prompts.json
│
├───log
│   │   logger_BotClass.log
│   │   logger_create_gpt_message_dict_from_twitchmsg.log
│   │   logger_msghistory_and_prompt.log
│   │   logger_openai_gpt_chatcompletion.log
│   │   logger_twitchio_helpers.log
│   │   logger_utils.log
│   │   logger_yaml_env.log
│   │   root_ArticleGenerator_logger.log
│   │   root_logger.log
│   │
│   └───ouat_story_history
│           final_ouat_temp_msg_history.json
├───my_modules
│   │   config.py
│   │   gpt.py
│   │   my_logging.py
│   │   text_to_speech.py
│   │   twitchio_helpers.py
│   │   utils.py
│   │   __init__.py
│   │
├───readme
│   │   README.md
│   │   README_games-countdown.md
│   │
│   └───helper_prompts
│           helper_prompts.md
│           prompt_building
│
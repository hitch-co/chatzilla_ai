@echo off

::Used for prompting user for custom username input or hardcoded username
:: set /p DISCORD_GAMES_COUNTDOWN_USERNAME="Enter your custom username: "
:: set DISCORD_GAMES_COUNTDOWN_USERNAME="eric"

::startup the flask app
start python C:/_repos/chatforme_bots/games_countdown_bot.py

::Wait
ping localhost -n 3 > nul

::Visit the app route to execute the games countdown command
::curl -X POST -H "Content-Type: application/json" -d "{\"DISCORD_GAMES_COUNTDOWN_BOT_USERNAME\":\"%DISCORD_GAMES_COUNTDOWN_BOT_USERNAME%\"}" http://localhost:5000/send_games_command
curl -X GET -H "Content-Type: application/json" http://localhost:5000/send_games_command

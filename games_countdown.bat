::.bat
@echo off

:: Prompt the user for the number of minutes.
set /p NUMBER_OF_MINUTES="Enter the number of minutes: "
REM set /p DISCORD_GAMES_COUNTDOWN_USERNAME="Enter your custom username: "

::startup the flask app
start python C:/_repos/chatforme_bots/games_countdown_bot.py

::Wait
ping localhost -n 5 > nul

:: Visit the app route to execute the games countdown command
curl -X GET -H "Content-Type: application/json" http://localhost:5000/send_games_command?number_of_minutes=%NUMBER_OF_MINUTES%

::Wait
ping localhost -n 5 > nul

exit
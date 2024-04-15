@echo off

:: Check if parameters are provided
if "%1"=="" (
    echo No environment provided.
    exit /b
)
if "%2"=="" (
    echo No port provided.
    exit /b
)

if "%3"=="" (
    echo No directory provided.
    exit /b
)

:: Environment and Port
set APP_BOT_USER_YAML=%1
set input_port_number=%2
set APP_DIRECTORY=%3

:: Switch directory 
cd "%APP_DIRECTORY%"

:: Activate venv
call ".\venv\Scripts\activate"

:: Set configuration path
set BOT_USER_CONFIG_PATH=config\bot_user_configs\%APP_BOT_USER_YAML%.yaml

:: Default prompt if not in interactive mode
set gpt_todo_prompt="Just plugging away, ask for details if you want to know more"

:: Run Python command with config and port
python twitch_bot.py

:: Delay for 3 seconds before opening browser
timeout /t 3

:: Open a browser and go to the localhost page
start http://localhost:%input_port_number%/auth

pause
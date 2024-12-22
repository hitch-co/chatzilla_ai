@echo off
setlocal enabledelayedexpansion

:: Check if parameters are provided
if "%~1"=="" (
    echo No environment provided.
    exit /b
)
if "%~2"=="" (
    echo No port provided.
    exit /b
)
if "%~3"=="" (
    echo No directory provided.
    exit /b
)

:: Environment and Port
set "APP_BOT_USER_YAML=%~1"
set "input_port_number=%~2"
set "TWITCH_BOT_ROOT_DIRECTORY=%~3"

:: Debugging - Print the variables
echo APP_BOT_USER_YAML=!APP_BOT_USER_YAML!
echo input_port_number=!input_port_number!
echo TWITCH_BOT_ROOT_DIRECTORY=!TWITCH_BOT_ROOT_DIRECTORY!

:: Switch directory 
cd "!TWITCH_BOT_ROOT_DIRECTORY!" || (
    echo Directory not found: !TWITCH_BOT_ROOT_DIRECTORY!
    exit /b
)
echo ...current directory: %cd%

:: Activate Conda environment
call "C:\Users\Admin\Miniconda3\condabin\conda.bat" activate openai_test_env

:: Set configuration path
set "BOT_USER_CONFIG_PATH=.\config\bot_user_configs\!APP_BOT_USER_YAML!"

:: Set the game to be played
set /p selected_game=What game are you playing today? (default:'no_game_selected'):
:: if selected game is empty or bad value, set to no_game_selected
echo ...starting twitch_bot.py
python twitch_bot.py

pause

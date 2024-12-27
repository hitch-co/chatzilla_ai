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

:: Validate MINICONDA_HOME
if "%MINICONDA_HOME%"=="" (
    echo MINICONDA_HOME is not set. Please configure your system environment variables.
    exit /b
)

:: Environment and Port
set "CHATZILLA_YAML_FILE=%~1"
set "CHATZILLA_PORT_NUMBER=%~2"
set "CHATZILLA_ROOT_DIRECTORY=%~3"

:: Debugging - Print the variables
echo CHATZILLA_YAML_FILE=!CHATZILLA_YAML_FILE!
echo CHATZILLA_PORT_NUMBER=!CHATZILLA_PORT_NUMBER!
echo CHATZILLA_ROOT_DIRECTORY=!CHATZILLA_ROOT_DIRECTORY!

:: Switch directory 
cd "!CHATZILLA_ROOT_DIRECTORY!" || (
    echo Directory not found: !CHATZILLA_ROOT_DIRECTORY!
    exit /b
)
echo ...current directory: %cd%

:: Activate Conda environment
call "%MINICONDA_HOME%\condabin\conda.bat" activate openai_chatzilla_ai_env || (
    echo Failed to activate Conda environment.
    exit /b
)

:: Set configuration path
set "CHATZILLA_YAML_PATH=.\config\bot_user_configs\!CHATZILLA_YAML_FILE!"

:: Set the game to be played
set /p selected_game=What game are you playing today? (default:'no_game_selected'):
echo ...starting twitch_bot.py
python twitch_bot.py
pause
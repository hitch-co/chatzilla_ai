@echo off
setlocal enabledelayedexpansion

:: Validate MINICONDA_HOME
if "%MINICONDA_HOME%"=="" (
    echo MINICONDA_HOME is not set. Please configure your system environment variables to include MINICONDA_HOME.
    exit /b
) else (
    if not exist "%MINICONDA_HOME%" (
        echo MINICONDA_HOME directory does not exist. Please check the path.
        exit /b
    )
)

:: Debugging - Print the variables
echo MINICONDA_HOME=!MINICONDA_HOME!
echo CHATZILLA_PORT_NUMBER=!CHATZILLA_PORT_NUMBER!
echo CHATZILLA_ROOT_DIRECTORY=!CHATZILLA_ROOT_DIRECTORY!

echo CHATZILLA_YAML_FILE=!CHATZILLA_YAML_FILE!
echo CHATZILLA_CONFIG_DIRPATH=!CHATZILLA_CONFIG_DIRPATH!
echo CHATZILLA_CONFIG_YAML_FILEPATH=!CHATZILLA_CONFIG_YAML_FILEPATH!

echo CHATZILLA_ENV_FILENAME=!CHATZILLA_ENV_FILENAME!
echo CHATZILLA_KEYS_ENV_DIRPATH=!CHATZILLA_KEYS_ENV_DIRPATH!
echo CHATZILLA_KEYS_ENV_FILENAME=!CHATZILLA_KEYS_ENV_FILENAME!

:: Switch directory 
cd "!CHATZILLA_ROOT_DIRECTORY!" || (
    echo Directory not found: !CHATZILLA_ROOT_DIRECTORY!
    exit /b
)
echo ...current directory: %cd%

:: Set the game to be played
set /p CHATZILLA_SELECTED_GAME=What game are you playing today? (default:'no_game_selected'):

:: Activate Conda environment
call "%MINICONDA_HOME%\condabin\conda.bat" activate openai_chatzilla_ai_env || (
    echo Failed to activate Conda environment.
    exit /b
)

:: Run preflight audio setup
python config/startup_audio_devices.py || (
    echo Audio setup failed. Exiting.
    exit /b
)

echo ...starting twitch_bot.py
python twitch_bot.py
pause
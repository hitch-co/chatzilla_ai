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

:: -- Ask about the game --
set /p CHATZILLA_SELECTED_GAME=What game are you playing today? (default:'no_game_selected'): 
if "%CHATZILLA_SELECTED_GAME%"=="" (
    set "CHATZILLA_SELECTED_GAME=no_game_selected"
)

:: -- If game is 'no_game_selected', ask about the stream --
if /I "%CHATZILLA_SELECTED_GAME%"=="no_game_selected" (
    goto :ask_stream
) else (
    set "CHATZILLA_SELECTED_STREAM=no_stream_selected"
    goto :skip_stream
)

:ask_stream
set /p CHATZILLA_SELECTED_STREAM=What type of stream are you watching? (default:'no_stream_selected'):
if "%CHATZILLA_SELECTED_STREAM%"=="" (
    set "CHATZILLA_SELECTED_STREAM=no_stream_selected"
)

:skip_stream

:: Debug (optional) - Print out the user choices
echo Selected Game: !CHATZILLA_SELECTED_GAME!
echo Selected Stream: !CHATZILLA_SELECTED_STREAM!

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

:: Run preflight audio setup
python config/startup_audio_devices.py || (
    echo Audio setup failed. Exiting.
    exit /b
)

echo ...starting twitch_bot.py
python twitch_bot.py
pause
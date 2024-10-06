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

:: Set Environment, Port, and Directory
set APP_BOT_USER_YAML=%1
set input_port_number=%2
set TWITCH_BOT_ROOT_DIRECTORY=%3

:: Debugging - Print the variables
echo APP_BOT_USER_YAML=%APP_BOT_USER_YAML%
echo input_port_number=%input_port_number%
echo TWITCH_BOT_ROOT_DIRECTORY=%TWITCH_BOT_ROOT_DIRECTORY%

:: Switch to the specified directory (worktree)
cd "%TWITCH_BOT_ROOT_DIRECTORY%"

:: Activate virtual environment from the worktree directory
call "..\chatzilla_ai\venv\Scripts\activate"

:: Set configuration path relative to the worktree directory
set BOT_USER_CONFIG_PATH=%TWITCH_BOT_ROOT_DIRECTORY%\config\bot_user_configs\%APP_BOT_USER_YAML%

:: Default prompt if not in interactive mode
set gpt_todo_prompt="Just plugging away, ask for details if you want to know more"

:: Set the game to be played
set /p selected_game=What game are you playing today? (default:'no_game_selected'):
if "%selected_game%"=="" set selected_game=no_game_selected

:: Run Python command with config and port
python twitch_bot.py

:: Delay for 3 seconds before opening the browser
timeout /t 3

:: Open a browser and go to the localhost page
start http://localhost:%input_port_number%/auth

pause

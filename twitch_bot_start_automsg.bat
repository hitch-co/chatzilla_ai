@echo off

:: Ask user to input param1
set /p prompt_list=Enter the value for the yaml prompt list: 
set /p include_sound=Should the bot run with audio?:

:: Check if param1 is empty and set to "standard" if so
if "%prompt_list%"=="" (
    set param1=standard
)

if "%include_sound%"=="" (
    set param1=False
)

:: Run Python command
python "C:\_repos\chatforme_bots\twitch_bot.py" --automated_msg_prompt_name %prompt_list% --include_sound %include_sound%

:: Open a browser and go to the localhost page
start http://localhost:3000/auth

:: Keep the window open
pause
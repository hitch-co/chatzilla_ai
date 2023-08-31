@echo off

:: Ask user to input param1
set /p prompt_list=Enter the value for param1: 

:: Check if param1 is empty and set to "standard" if so
if "%param1%"=="" (
    set param1=standard
)

:: Run Python command
python "C:\_repos\chatforme_bots\twitch_bot.py" --automated_msg_prompt_name %prompt_list%

:: Open a browser and go to the localhost page
start http://localhost:3000/auth

:: Keep the window open
pause
@echo off

:: Ask user to input param1
set /p prompt_list_automsg=Enter the value for the yaml automsg prompt list:
set /p prompt_list_chatforme=Enter the value for the yaml chatforme prompt list:  
set /p include_sound=Should the bot run with audio?:
set /p input_port_number=What port number would you like to run the app on?:

:: Check if param1 is empty and set to "standard" if so
if "%prompt_list%"=="" (
    set param1=standard
)

if "%include_sound%"=="" (
    set param1=False
)

:: Run Python command
python "C:\_repos\chatforme_bots\twitch_bot.py" --automated_msg_prompt_name %prompt_list_automsg% --include_sound %include_sound% --input_port_number=%input_port_number% --chatforme_prompt_name=%prompt_list_chatforme%

:: Open a browser and go to the localhost page
start http://localhost:%input_port_number%/auth

:: Keep the window open
pause
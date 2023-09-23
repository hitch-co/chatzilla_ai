@echo off

:: Ask user to input param1
set /p include_automsg=Would you like to run AUTOMSG bot (default: no)?
set /p include_sound=Should the bots run with AUDIO (default: no)?:

set /p prompt_list_automsg=Enter the value for the yaml AUTOMSG prompt list (default: standard):
set /p prompt_list_chatforme=Enter the value for the yaml CHATFORME prompt list (default: standard):  

set /p input_port_number=What PORT NUMBER would you like to run the app on? (default:3000):


:: Run Python command
python "C:\_repos\chatforme_bots\twitch_bot.py" --automated_msg_prompt_name %prompt_list_automsg% --include_sound %include_sound% --input_port_number=%input_port_number% --chatforme_prompt_name=%prompt_list_chatforme%

:: Open a browser and go to the localhost page
start http://localhost:%input_port_number%/auth

:: Keep the window open
pause
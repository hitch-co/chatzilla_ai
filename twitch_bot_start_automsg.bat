@echo off

:: Ask user to input param1
set /p include_ouat=Would you like to run OnceUponATime bot (default: yes)?
set /p include_automsg=Would you like to run AUTOMSG bot (default: no)?
set /p include_sound=Should the bots run with AUDIO (default: no)?:

set /p prompt_list_ouat=Enter the value for the yaml OnceUponATime prompt list (default: onceuponatime):
set /p prompt_list_automsg=Enter the value for the yaml AUTOMSG prompt list (default: standard):
set /p prompt_list_chatforme=Enter the value for the yaml CHATFORME prompt list (default: standard):  

set /p input_port_number=What PORT NUMBER would you like to run the app on? (default:3000):

@REM SET DEFAULT VALUES.  Can't get the defaults  in arg parser to work as I planned (aka leaving the command prompt entry 
@REM empty.)  Defaults in arg parser could thus be confusing as they are useless!
if "%include_ouat%"=="" (
    set include_ouat=yes
)
if "%include_automsg%"=="" (
    set include_automsg=no
)
if "%include_sound%"=="" (
    set include_sound=no
)
if "%prompt_list_ouat%"=="" (
    set prompt_list_ouat=onceuponatime
)
if "%prompt_list_automsg%"=="" (
    set prompt_list_automsg=videogames
)
if "%prompt_list_chatforme%"=="" (
    set prompt_list_chatforme=standard
)

if "%input_port_number%"=="" (
    set input_port_number=3000
)

:: Run Python command
python "C:\_repos\chatforme_bots\twitch_bot.py" ^
    --include_ouat=%include_ouat% --ouat_prompt_name=%prompt_list_ouat% ^
    --include_automsg=%include_automsg% --automated_msg_prompt_name=%prompt_list_automsg% ^
    --chatforme_prompt_name=%prompt_list_chatforme% ^
    --include_sound=%include_sound% ^
    --input_port_number=%input_port_number% 

:: Open a browser and go to the localhost page
start http://localhost:%input_port_number%/auth

:: Keep the window open
pause
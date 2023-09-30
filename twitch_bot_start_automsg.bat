@echo off

:: Set default values
set include_ouat=yes
set include_automsg=no
set include_sound=no
set prompt_list_ouat=newsarticle_og
set prompt_list_automsg=videogames
set prompt_list_chatforme=standard
set input_port_number=3000

:: Ask user to input param1
set /p include_ouat=Would you like to run OnceUponATime bot (default:"%include_ouat%")?
set /p include_automsg=Would you like to run AUTOMSG bot (default:"%include_automsg%")?
set /p include_sound=Should the bots run with AUDIO (default:"%include_sound%")?:

set /p prompt_list_ouat=Enter the value for the yaml OnceUponATime prompt list (default:"%prompt_list_ouat%"):
set /p prompt_list_automsg=Enter the value for the yaml AUTOMSG prompt list (default:"%prompt_list_automsg%"):
set /p prompt_list_chatforme=Enter the value for the yaml CHATFORME prompt list (default:"%prompt_list_chatforme%"):  

set /p input_port_number=What PORT NUMBER would you like to run the app on? (default:"%input_port_number%"):

:: Run Python command
python "C:\_repos\chatforme_bots\twitch_bot.py" ^
    --include_ouat=%include_ouat% --ouat_prompt_name=%prompt_list_ouat% ^
    --include_automsg=%include_automsg% --automated_msg_prompt_name=%prompt_list_automsg% ^
    --chatforme_prompt_name=%prompt_list_chatforme% ^
    --include_sound=%include_sound% ^
    --input_port_number=%input_port_number% 

:: Delay for 5 seconds
timeout /t 3

:: Open a browser and go to the localhost page
start http://localhost:%input_port_number%/auth

:: Keep the window open
pause
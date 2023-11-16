@echo off

:: Set default values
set include_ouat=yes
set include_automsg=no
set include_sound=no
set prompt_list_ouat=newsarticle_dynamic
set prompt_list_automsg=videogames
set prompt_list_chatforme=standard
set input_port_number=3000

@REM :: Ask user to input param1
@REM set /p include_ouat=Would you like to run OnceUponATime bot (default:"%include_ouat%")?
@REM set /p include_automsg=Would you like to run AUTOMSG bot (default:"%include_automsg%")?
@REM set /p include_sound=Should the bots run with AUDIO (default:"%include_sound%")?:

@REM set /p prompt_list_ouat=Enter the value for the yaml OnceUponATime prompt list (default:"%prompt_list_ouat%"):
@REM set /p prompt_list_automsg=Enter the value for the yaml AUTOMSG prompt list (default:"%prompt_list_automsg%"):
@REM set /p prompt_list_chatforme=Enter the value for the yaml CHATFORME prompt list (default:"%prompt_list_chatforme%"):  

@REM set /p input_port_number=What PORT NUMBER would you like to run the app on? (default:"%input_port_number%"):

:: Run Python command
python ".\twitch_bot.py" 

:: Delay for 5 seconds
timeout /t 3

:: Open a browser and go to the localhost page
start http://localhost:%input_port_number%/auth

:: Keep the window open
pause
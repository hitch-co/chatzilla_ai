@echo off

:: Activate venv
call "C:\_repos\chatzilla_ai_prod\chatzilla_ai\venv\Scripts\activate"

:: Set default values
set prompt_list_ouat=newsarticle_dynamic
set prompt_list_automsg=videogames
set prompt_list_chatforme=standard

set include_ouat=yes
set include_automsg=no
set include_sound=no
set input_port_number=3000

@REM :: user to input
@REM set /p include_ouat=Would you like to include the STORYTELLER? (default:"%include_ouat%")?
@REM set /p include_automsg=Would you like to run AUTOMSG? (default:"%include_automsg%")?
@REM set /p include_sound=Should the bot run with AUDIO? (default:"%include_sound%")?:
@REM set /p input_port_number=What PORT NUMBER would you like to run the app on? (default:"%input_port_number%"):

:: Run Python command
python ".\twitch_bot.py"

:: Delay for 5 seconds
timeout /t 3

:: Open a browser and go to the localhost page
start http://localhost:%input_port_number%/auth

pause
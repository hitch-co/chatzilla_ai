@echo off

:: Activate venv
call "C:\_repos\chatzilla_ai\venv\Scripts\activate"

set input_port_number=3001
set /p gpt_todo_prompt=What would you like to share about your tasklist on todays stream? (default:"Just plugging away, ask for details if you want to know more"):

@REM :: user to input
@REM set /p input_port_number=What PORT NUMBER would you like to run the app on? (default:"%input_port_number%"):

:: Run Python command
python ".\twitch_bot.py"

:: Delay for 2 seconds
timeout /t 2

:: Open a browser and go to the localhost page
start http://localhost:%input_port_number%/auth

pause
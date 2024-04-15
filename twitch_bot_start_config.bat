@REM @echo off

@REM :: Switch directory 
@REM cd "C:\_repos\chatzilla_ai_config\chatzilla_ai"

@REM :: Activate venv
@REM call ".\env\Scripts\activate"

@REM :: Set default values
@REM set input_port_number=3000
@REM set /p gpt_todo_prompt=What would you like to share about your tasklist on todays stream? (default:"Just plugging away, ask for details if you want to know more"):

@REM :: Run Python command
@REM python ".\twitch_bot.py"

@REM :: Delay for 5 seconds
@REM timeout /t 3

@REM :: Open a browser and go to the localhost page
@REM start http://localhost:%input_port_number%/auth

@REM pause
REM 1) Load variables from .env
if exist .\config\.env (
  for /f "usebackq tokens=1,* delims== " %%i in (`type .\config\.env`) do (
    set "%%i=%%j"
  )
)

:: Start Ollama in the same window
"C:\Users\Admin\AppData\Local\Programs\Ollama\ollama.exe" run deepseek-r1:7b  > log/ollama_stdout.log  2> log/ollama_stderr.log

:: Start Ollama in a new window
@REM start "Ollama DeepSeek" ^
@REM     "C:\Users\Admin\AppData\Local\Programs\Ollama\ollama.exe" run deepseek-r1:7b

run_environment.bat
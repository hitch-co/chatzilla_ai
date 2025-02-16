@echo off 

::Load variables from .env
if exist .\config\.env (
  for /f "usebackq tokens=1,* delims== " %%i in (`type .\config\.env`) do (
    set "%%i=%%j"
  )
)

run_environment.bat
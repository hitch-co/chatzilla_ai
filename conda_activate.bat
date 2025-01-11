@echo off
setlocal

if not defined MINICONDA_HOME (
    echo MINICONDA_HOME environment variable is not set.
    exit /b 1
)

%MINICONDA_HOME%\condabin\conda.bat activate openai_chatzilla_ai_env
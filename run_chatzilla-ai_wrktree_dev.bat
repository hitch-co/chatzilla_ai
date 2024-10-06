@echo off
:: Check if branch name is provided
if "%1"=="" (
    echo No branch name provided.
    exit /b
)

:: Set the worktree path based on the branch name
set branch_name=%1
set worktree_path="C:\_repos\chatzilla_ai_worktrees\%branch_name%-worktree"

:: Call the run_environment.bat with environment, port, and the new worktree path
call run_environment.bat chatzilla_ai_ehitch.yaml 3001 %worktree_path%
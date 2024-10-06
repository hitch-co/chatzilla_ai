@echo off

:: Prompt for branch name to create a worktree
set /p branch_name=Enter the branch name: 

:: Check if branch name is provided
if "%branch_name%"=="" (
    echo No branch name provided.
    exit /b
)

:: Set the worktree path based on the branch name
set worktree_path=C:\_repos\chatzilla_ai_worktrees\%branch_name%-worktree

:: Debugging - print the worktree path to make sure it is correctly constructed
echo Worktree path: %worktree_path%

:: Call the run_environment.bat with environment, port, and the new worktree path
call run_environment.bat chatzilla_ai_ehitch.yaml 3001 %worktree_path%

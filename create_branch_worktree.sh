#!/bin/bash

# STEPS
# 1. Clone the repo
# 2. Setup a Python environment (ensure requirements.txt is run)

#########################################################
# Define the directory name for the repo and worktrees
REPO_DIR="/c/_repos/chatzilla_ai"
WORKTREES_DIR="/c/_repos/chatzilla_ai_worktrees"

#########################################################

# Prompt for the branch name
read -p "Enter the branch name: " BRANCH_NAME
echo "Branch Name: '$BRANCH_NAME'"

# Check if a branch name was provided
if [ -z "$BRANCH_NAME" ]; then
    echo "No branch name provided. Exiting."
    exit 1
fi

# Validate the branch name format (ensure no underscores)
if [[ $BRANCH_NAME =~ _ ]]; then
    echo "Invalid branch name format. Branch names should not contain underscores."
    read -p "Are you sure you want to proceed despite the format error? (y/n): " confirm
    if [[ $confirm != "y" ]]; then
        echo "Exiting script due to invalid format."
        exit 1
    fi
fi

# Check if the worktrees directory exists, if not, create it
WORKTREE_DIR="${WORKTREES_DIR}/${BRANCH_NAME}-worktree"
if [ ! -d "$(dirname "$WORKTREE_DIR")" ]; then
    echo "'chatzilla_ai_worktrees' directory not found. Creating it now..."
    mkdir -p "$(dirname "$WORKTREE_DIR")"
fi

# Ensure the worktree directory does not already exist
if [ -d "$WORKTREE_DIR" ]; then
    echo "A directory for the worktree '${BRANCH_NAME}' already exists. Exiting."
    exit 1
fi

# Create the worktree and a new branch from 'origin/master'
if git worktree add "$WORKTREE_DIR" -b "$BRANCH_NAME" origin/master; then
    echo "Worktree and new branch '${BRANCH_NAME}' created at '${WORKTREE_DIR}'"
    
    # Push the branch to origin
    git -C "$WORKTREE_DIR" push -u origin "$BRANCH_NAME"
else
    echo "Failed to create worktree and branch. Exiting."
    exit 1
fi

# Navigate to the worktree directory
cd "$WORKTREE_DIR" || exit

# Leave a note for the user to install dependencies
echo "Note: Remember to install dependencies by running:"
echo "  pip install -r requirements.txt"

# Open Visual Studio Code at the worktree directory
code "$WORKTREE_DIR"
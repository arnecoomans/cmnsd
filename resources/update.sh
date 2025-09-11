#!/bin/bash
# Update script for Django applications with submodule support
# Runs a git pull and updates submodules if necessary
# If updates are detected, it activates the virtual environment,
# installs new requirements, runs migrations, and collects static files
# Restarts the application with supervisorctl
# based on the directory name (first part before the first dot)
# Author: Arne Coomans
# Version: 1.2.0

# Change to the script's directory
cd "$(dirname "$0")"

# Pull latest changes from Git
echo "Pulling latest changes from Git..."
git_output=$(git pull 2>&1)

# Check if git pull was successful
if [ $? -ne 0 ]; then
  echo "Error during git pull:"
  echo "$git_output"
  exit 1
fi

echo "Git pull complete."

# Check if there were any updates
if echo "$git_output" | grep -q 'Already up to date'; then
  echo "No changes detected. Checking for submodule updates..."
else
  echo "Changes detected in the main repository."
fi

# Check for submodules
if [ -f .gitmodules ]; then
  echo "Checking for submodule updates..."
  git submodule update --init --recursive

  # Ensure submodules track a branch instead of being in a detached HEAD state
  git submodule foreach --recursive 'git checkout $(git config -f $toplevel/.gitmodules submodule.$name.branch || echo main)'

  # Update submodules to the latest commit on their tracked branch
  git submodule update --remote --merge

  # Detect changes in submodules
  submodule_changes=$(git diff --submodule=log)

  # If there are changes in submodules, update again to ensure consistency
  git submodule update --init --recursive
  if [ -z "$submodule_changes" ]; then
    echo "No updates detected in submodules."
  else
    echo "Submodule updates detected."
  fi
fi

# Combine changes from main repo and submodules
all_changes="$git_output
$submodule_changes"

# Check if any relevant files have changed (migrations, static files, or requirements.txt)
if echo "$all_changes" | grep -q -e 'migration' -e 'static' -e 'requirements.txt'; then
  echo "Changes detected in requirements, migrations, static files, or submodules. Activating virtual environment..."
  
  # Activate virtual environment in .venv directory in the current directory
  source .venv/bin/activate
  echo "Virtual environment activated."

  # Install any new requirements
  if echo "$all_changes" | grep -q 'requirements.txt'; then
    echo "Installing new requirements..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    echo "Requirements installed."
  else
    echo "No changes in requirements detected. Skipping requirement installation."
  fi

  # Run migrations if needed
  if echo "$all_changes" | grep -q 'migration'; then
    echo "Running migrations..."
    python manage.py migrate
    echo "Migrations complete."
  else
    echo "No changes in migrations detected. Skipping migration."
  fi
  
  # Collect static files if needed
  if echo "$all_changes" | grep -q 'static'; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
    echo "Static files collected."
  else
    echo "No changes in static files detected. Skipping collectstatic."
  fi
else
  echo "No relevant changes detected. Skipping migrations and static collection."
fi

# Extract the first word from the current directory name, split by '.'
pool_name=$(basename "$PWD" | cut -d. -f1)

# Restart the application with supervisor using the extracted pool name
echo "Restarting application with supervisor for pool '$pool_name'..."
sudo supervisorctl restart "$pool_name"
echo "Application restart for pool '$pool_name' complete."

#!/bin/bash
# Update script for Django applications with submodule support.
# Pulls the repository and its submodules, then - with the project's
# virtual environment - installs requirements when a requirements file
# changed, and always runs migrations and collectstatic (both idempotent
# and cheap when nothing changed; a skipped collectstatic breaks pages
# with hashed static file names). Then the project's own .post_update.sh,
# if there is one, and a restart with supervisorctl, the program named
# after the directory (the first part before the first dot).
#
# .post_update.sh (optional, executable, in the project root, versioned
# with the project): site-specific steps, run with the virtual environment
# active, just before the restart. It gets UPDATE_CHANGED=1 when the pull
# brought changes (in the repository or a submodule), else 0.
#
# Changes are detected by commit, not by reading git's output: the
# repository's and each submodule's commit before and after, and the files
# that changed between them.
#
# Author: Arne Coomans
# Version: 1.3.0

# Change to the repository root
cd "$(git rev-parse --show-toplevel)" || {
  echo "Error: could not determine repository root."
  exit 1
}

# --- The repository -------------------------------------------------------

before=$(git rev-parse HEAD)
echo "Pulling latest changes from Git..."
git_output=$(git pull 2>&1)
if [ $? -ne 0 ]; then
  echo "Error during git pull:"
  echo "$git_output"
  exit 1
fi
echo "$git_output"
after=$(git rev-parse HEAD)

changed_files=""
if [ "$before" != "$after" ]; then
  changed_files=$(git diff --name-only "$before" "$after")
  echo "Changes in the repository: $(echo "$changed_files" | wc -l | tr -d ' ') file(s)."
else
  echo "No changes in the repository."
fi

# --- A local cmnsd checkout that isn't a submodule (manual pull safeguard) --

if ! grep -q 'path = cmnsd' .gitmodules 2>/dev/null && { [ -f "cmnsd/.git" ] || [ -d "cmnsd/.git" ]; }; then
  echo "Detected a local cmnsd repository. Pulling latest changes..."
  cmnsd_before=$(git -C cmnsd rev-parse HEAD)
  if ! git -C cmnsd pull; then
    echo "Error during git pull in cmnsd."
    exit 1
  fi
  cmnsd_after=$(git -C cmnsd rev-parse HEAD)
  if [ "$cmnsd_before" != "$cmnsd_after" ]; then
    changed_files="$changed_files
$(git -C cmnsd diff --name-only "$cmnsd_before" "$cmnsd_after" | sed 's#^#cmnsd/#')"
  fi
fi

# --- Submodules -------------------------------------------------------------

if [ -f .gitmodules ]; then
  echo "Updating submodules..."
  git submodule update --init --recursive
  # Each submodule on its configured branch (default main).
  git submodule foreach --quiet --recursive 'git checkout -q $(git config -f $toplevel/.gitmodules submodule.$name.branch || echo main)'

  # Commits before, then the latest of each tracked branch, then after.
  submodules_before=$(git submodule foreach --quiet --recursive 'echo "$displaypath $(git rev-parse HEAD)"')
  git submodule update --remote --merge

  while read -r path old; do
    [ -z "$path" ] && continue
    new=$(git -C "$path" rev-parse HEAD)
    if [ "$old" != "$new" ]; then
      echo "Submodule $path updated."
      changed_files="$changed_files
$(git -C "$path" diff --name-only "$old" "$new" | sed "s#^#$path/#")"
    else
      echo "Submodule $path: no changes."
    fi
  done <<< "$submodules_before"
else
  echo "No .gitmodules file found. Skipping submodule updates."
fi

changed_files=$(echo "$changed_files" | sed '/^$/d')
update_changed=0
[ -n "$changed_files" ] && update_changed=1

# --- The application --------------------------------------------------------

if [ -d ".venv/bin" ]; then
  source .venv/bin/activate
  echo "Virtual environment activated."
else
  echo "Warning: .venv not found - running with the system's Python."
fi

# Requirements: only when a requirements file changed (the slow step).
if echo "$changed_files" | grep -q 'requirements.txt$'; then
  echo "Installing requirements..."
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
else
  echo "No requirements changed."
fi

# Migrations and static files: always - idempotent, and nothing gets missed.
echo "Running migrations..."
python manage.py migrate --noinput || exit 1
echo "Collecting static files..."
python manage.py collectstatic --noinput || exit 1

# The project's own steps.
if [ -x ".post_update.sh" ]; then
  echo "Running .post_update.sh..."
  UPDATE_CHANGED=$update_changed ./.post_update.sh || {
    echo "Error: .post_update.sh failed - not restarting."
    exit 1
  }
elif [ -f ".post_update.sh" ]; then
  echo "Warning: .post_update.sh is not executable (chmod +x .post_update.sh) - skipped."
fi

# Restart with supervisor, the program named after the directory's first part.
pool_name=$(basename "$PWD" | cut -d. -f1)
echo "Restarting application with supervisor for '$pool_name'..."
sudo supervisorctl restart "$pool_name"
echo "Restart of '$pool_name' complete."

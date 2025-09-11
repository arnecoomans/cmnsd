#!/usr/bin/env python3
"""
Update script for Django applications with submodule support.
Performs a git pull, updates submodules (and ensures the submodules are on the correct branch),
checks if there are changes in migrations, static files, or requirements.txt,
activates the virtual environment, installs new requirements, runs migrations,
collects static files and finally restarts the application with supervisorctl.

# Author: Arne Coomans
# Version: 1.3.0

"""

import os
import sys
import subprocess
import shlex
from pathlib import Path

def run_command(cmd, cwd=None, capture_output=True, text=True, check=True):
    """Wrapper om een command uit te voeren en de output terug te geven."""
    print(f"Running command: {cmd}")
    result = subprocess.run(shlex.split(cmd), cwd=cwd, capture_output=capture_output, text=text)
    if check and result.returncode != 0:
        print(f"Command failed: {cmd}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        sys.exit(result.returncode)
    return result

def update_main_repo():
    print("Pulling latest changes from Git (main repository)...")
    result = run_command("git pull", capture_output=True, text=True, check=False)
    git_output = result.stdout + result.stderr

    if result.returncode != 0:
        print("Error during git pull:")
        print(git_output)
        sys.exit(1)

    print("Git pull complete.")
    if "Already up to date" in git_output:
        print("No changes detected in main repository.")
    else:
        print("Changes detected in the main repository.")

    return git_output

def update_submodules():
    submodule_changes = ""
    static_changes_in_submodules = False

    gitmodules = Path(".gitmodules")
    if gitmodules.exists():
        print("Checking for submodule updates...")
        # Initialize/update submodules recursively.
        run_command("git submodule update --init --recursive")

        # Ensure each submodule is on its tracked branch.
        run_command("git submodule foreach --recursive 'git checkout $(git config -f $toplevel/.gitmodules submodule.$name.branch || echo main)'")

        # Update submodules to the latest commit on their tracked branch.
        run_command("git submodule update --remote --merge")

        # Get diff for submodules
        result = run_command("git diff --submodule=log", capture_output=True, text=True, check=False)
        submodule_changes = result.stdout.strip()

        # Na update opnieuw initialiseren om consistentie te verzekeren.
        run_command("git submodule update --init --recursive")

        if submodule_changes:
            print("Submodule updates detected:")
            print(submodule_changes)
        else:
            print("No updates detected in submodules.")

        # Controleer voor elke submodule of er wijzigingen zijn in een "static/"-map.
        # Hiervoor lezen we de paden uit .gitmodules en controleren we per submodule.
        submodules = []
        with open(gitmodules) as f:
            for line in f:
                if line.strip().startswith("path"):
                    # line voorbeeld: path = submodule_dir
                    _, path_value = line.split("=")
                    submodules.append(path_value.strip())
        for submodule in submodules:
            submodule_path = Path(submodule)
            if submodule_path.exists():
                # Vergelijk de laatste twee commits in de submodule.
                # Opmerking: dit werkt alleen als de submodule minstens 2 commits heeft.
                try:
                    head_commit = run_command("git rev-parse HEAD", cwd=submodule, capture_output=True).stdout.strip()
                    # Bepaal een vorige commit: HEAD~1
                    prev_commit = run_command("git rev-parse HEAD~1", cwd=submodule, capture_output=True).stdout.strip()
                    diff_result = run_command(f"git diff --name-only {prev_commit} {head_commit}", cwd=submodule, capture_output=True)
                    changed_files = diff_result.stdout.strip().splitlines()
                    for file in changed_files:
                        if file.startswith("static"):
                            print(f"Detected static changes in submodule '{submodule}': {file}")
                            static_changes_in_submodules = True
                            break  # Eén wijziging is voldoende
                except Exception as e:
                    print(f"Warning: could not determine diff for submodule {submodule}: {e}")
            else:
                print(f"Warning: submodule path {submodule} does not exist.")
    else:
        print("No .gitmodules file found. Skipping submodule updates.")

    return submodule_changes, static_changes_in_submodules

def modify_env_for_venv():
    """Wijzig de omgeving zodat de virtual environment in .venv/bin eerst in PATH staat."""
    venv_path = Path(".venv/bin")
    if venv_path.exists():
        new_path = str(venv_path.resolve()) + os.pathsep + os.environ.get("PATH", "")
        os.environ["PATH"] = new_path
        print("Virtual environment adjusted in PATH.")
    else:
        print("No .venv/bin directory found. Proceeding without virtual environment adjustments.")

def main():
    # Zorg dat het script in zijn eigen directory draait
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    print(f"Changed directory to {script_dir}")

    git_output = update_main_repo()
    submodule_changes, static_submodule_flag = update_submodules()

    # Combineer veranderingen van main repo en submodules.
    all_changes = git_output + "\n" + submodule_changes

    # Check op relevante wijzigingen: migrations, static files, of requirements.txt.
    relevant_change = False
    if ("migration" in all_changes.lower() or
        "requirements.txt" in all_changes.lower() or
        "static" in all_changes.lower() or
        static_submodule_flag):
        relevant_change = True

    if relevant_change:
        print("Changes detected in requirements, migrations, static files, or submodules.")
        modify_env_for_venv()

        # Installeer nieuwe requirements als requirements.txt gewijzigd is.
        if "requirements.txt" in all_changes:
            print("Installing new requirements...")
            run_command("python -m pip install --upgrade pip")
            run_command("python -m pip install -r requirements.txt")
            print("Requirements installed.")
        else:
            print("No changes in requirements detected. Skipping requirement installation.")

        # Voer migraties uit als er migratiewijzigingen zijn.
        if "migration" in all_changes.lower():
            print("Running migrations...")
            run_command("python manage.py migrate")
            print("Migrations complete.")
        else:
            print("No changes in migrations detected. Skipping migration.")

        # Voer collectstatic uit als er wijzigingen in static files zijn.
        # Hierbij wordt ook specifiek gekeken of er in submodules static changes zijn.
        if "static" in all_changes.lower() or static_submodule_flag:
            print("Collecting static files...")
            run_command("python manage.py collectstatic --noinput")
            print("Static files collected.")
        else:
            print("No changes in static files detected. Skipping collectstatic.")
    else:
        print("No relevant changes detected. Skipping migrations and static collection.")

    # Bepaal de poolnaam door de eerste token (voor de eerste punt) van de huidige directorynaam.
    current_dir = Path.cwd().name
    pool_name = current_dir.split(".")[0]
    print(f"Restarting application with supervisor for pool '{pool_name}'...")
    run_command(f"sudo supervisorctl restart {pool_name}")
    print(f"Application restart for pool '{pool_name}' complete.")

if __name__ == "__main__":
    main()
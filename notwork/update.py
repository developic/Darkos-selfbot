import os
import json
import subprocess
from rich.console import Console
from time import sleep

console = Console()

# Load the previous config if it exists
if os.path.exists("config.json"):
    with open("config.json", "r") as config_file:
        prev_config_dict = json.load(config_file)
else:
    prev_config_dict = {}

def deep_merge_carry_over(base, new):
    result = {}

    for key, value in new.items():
        if key in base:
            if isinstance(value, dict) and isinstance(base[key], dict):
                result[key] = deep_merge_carry_over(base[key], value)
            else:
                # Use the existing value from base
                result[key] = base[key]
        else:
            # Use the default value from new
            result[key] = value

    return result

def merge_json_carry_over():
    if not os.path.exists("config.json"):
        console.log("[yellow]config.json not found. Recreating from previous configuration...")
        with open("config.json", "w") as f:
            json.dump(prev_config_dict, f, indent=4)

    with open("config.json", 'r') as main_file:
        main_data = json.load(main_file)

    updated_data = deep_merge_carry_over(prev_config_dict, main_data)

    with open("config.json", 'w') as output_file:
        json.dump(updated_data, output_file, indent=4)

def pull_latest_changes_git():
    repo_dir = "."
    os.chdir(repo_dir)

    # Check for uncommitted changes
    with console.status("[bold green]Checking for uncommitted changes...") as status:
        status_result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)

    if status_result.stdout:
        console.log("[yellow]Uncommitted changes detected. Stashing changes...")
        with console.status("[bold yellow]Stashing changes...") as status:
            subprocess.run(['git', 'stash'])
            sleep(1)

    # Check for untracked files
    with console.status("[bold cyan]Checking for untracked files...") as status:
        untracked_files = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], capture_output=True, text=True)

    if untracked_files.stdout:
        console.log("[yellow]Untracked files detected. Cleaning up untracked files...")
        with console.status("[bold red]Cleaning untracked files...") as status:
            subprocess.run(['git', 'clean', '-f', "-d"])
            sleep(1)

    # Pull the latest changes
    with console.status("[bold green]Pulling the latest changes from origin/main...") as status:
        subprocess.run(['git', 'checkout', 'main'])
        subprocess.run(['git', 'pull', 'origin', 'main'])
        sleep(1)

    # Merge configuration
    console.log("[bold green]Update complete!")
    console.log("[bold green]Attempting to merge previous config with the updated config...")
    merge_json_carry_over()

# Run the update process
pull_latest_changes_git()
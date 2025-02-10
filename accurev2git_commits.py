import os
import subprocess
import argparse
import datetime
import re

def run_command(command, cwd=None, exit_on_fail=True):
    """Executes a shell command and returns the output. Handles errors gracefully."""
    result = subprocess.run(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        error_message = f"❌ Error running command: {command}\n{result.stderr}"
        print(error_message)
        
        # Log errors to a file
        with open("accurev_migration_errors.log", "a") as error_log:
            error_log.write(f"{datetime.datetime.now()} - {error_message}\n")

        if exit_on_fail:
            exit(1)
        return None  # Return None for error cases
    
    return result.stdout.strip()

def migrate_accurev_to_git(stream_name, git_repo_path):
    """Migrates AccuRev stream history into a Git repository."""
    
    # Log into AccuRev
    accurev_login()

    # Create workspace
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    workspace_name = f"accurev_{stream_name}_ws_{timestamp}"
    target_dir = os.path.join(git_repo_path, stream_name)
    os.makedirs(target_dir, exist_ok=True)

    print(f"🛠️ Creating new workspace: {workspace_name}")
    run_command(f"accurev mkws -w {workspace_name} -b {stream_name} -l {target_dir}")

    # Initialize Git
    if not os.path.exists(os.path.join(git_repo_path, ".git")):
        run_command(f"git init", cwd=git_repo_path)
        run_command(f"git checkout master", cwd=git_repo_path)

    # Get AccuRev transaction history
    transactions = get_accurev_history(stream_name)

    # Apply AccuRev transactions as Git commits
    for txn in transactions:
        print(f"🚀 Processing Transaction: {txn['txn_id']} by {txn['user']} on {txn['date']}")

        # Populate workspace with transaction state
        pop_result = run_command(f"accurev pop -t {txn['txn_id']} -R -O -L {target_dir}", exit_on_fail=False)
        if pop_result is None:
            print(f"⚠️ Skipping Transaction {txn['txn_id']} due to errors.")
            continue  # Skip this commit and move to the next one

        # Add files to Git
        run_command(f"git add .", cwd=git_repo_path)

        # Ensure commit message is not empty
        commit_message = txn["message"] if txn["message"] else f"AccuRev Transaction {txn['txn_id']}"

        # Commit with original author and timestamp
        commit_cmd = (
            f'GIT_COMMITTER_DATE="{txn["date"]}" GIT_AUTHOR_DATE="{txn["date"]}" '
            f'git commit --author="{txn["user"]} <{txn["user"]}@accurev.com>" --date="{txn["date"]}" '
            f'-m "{commit_message}"'
        )
        run_command(commit_cmd, cwd=git_repo_path)

    # Push to remote Git repository
    run_command(f"git push origin master", cwd=git_repo_path)

    print(f"✅ Successfully migrated AccuRev stream '{stream_name}' history to Git.")

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

def accurev_login():
    """Ensures the user is logged into AccuRev to avoid session expiration."""
    print("🔄 Logging into AccuRev...")
    run_command("accurev login jp_adm AccPass123")  # Change credentials accordingly

def parse_accurev_history(history_output):
    """Parses the text-based AccuRev history output into structured data."""
    transactions = []
    lines = history_output.split("\n")
    current_txn = None

    for line in lines:
        txn_match = re.match(r"transaction (\d+); promote; ([\d/]+ [\d:]+) ; user: (.+)", line)
        if txn_match:
            if current_txn:
                transactions.append(current_txn)  # Save the previous transaction
            
            txn_id, date_str, user = txn_match.groups()
            txn_time = datetime.datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S")
            git_date = txn_time.strftime("%Y-%m-%dT%H:%M:%S")
            current_txn = {"txn_id": txn_id, "user": user, "date": git_date, "message": ""}

        elif current_txn and line.startswith("  #"):
            current_txn["message"] = line.strip("  #").strip()

    if current_txn:
        transactions.append(current_txn)  # Save the last transaction

    return transactions[::-1]  # Reverse to apply oldest commits first

def get_accurev_history(stream_name):
    """Retrieves and parses AccuRev transaction history for a given stream."""
    print(f"📜 Fetching AccuRev history for stream '{stream_name}'...")
    history_cmd = f"accurev hist -s {stream_name} -t now.1000"
    history_output = run_command(history_cmd)
    
    if not history_output:
        print(f"⚠️ No history found for stream '{stream_name}'.")
        exit(1)
    
    return parse_accurev_history(history_output)

def migrate_accurev_to_git(stream_name, git_repo_path):
    """Migrates AccuRev stream history into a Git repository."""
    
    # Step 1: Log into AccuRev
    accurev_login()

    # Step 2: Create a new unique workspace
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    workspace_name = f"accurev_{stream_name}_ws_{timestamp}"
    target_dir = os.path.join(git_repo_path, stream_name)
    os.makedirs(target_dir, exist_ok=True)

    print(f"🛠️ Creating new workspace: {workspace_name}")
    run_command(f"accurev mkws -w {workspace_name} -b {stream_name} -l {target_dir}")

    # Step 3: Ensure the workspace is updated before popping files
    print("🔄 Updating AccuRev workspace...")
    run_command(f"accurev update", cwd=target_dir)

    # Step 4: Initialize Git if not already initialized
    if not os.path.exists(os.path.join(git_repo_path, ".git")):
        run_command(f"git init", cwd=git_repo_path)
        run_command(f"git checkout master", cwd=git_repo_path)

    # Step 5: Get AccuRev transaction history
    transactions = get_accurev_history(stream_name)

    # Step 6: Apply each AccuRev version as a Git commit
    for txn in transactions:
        print(f"🚀 Processing Transaction: {txn['txn_id']} by {txn['user']} on {txn['date']}")

        # 🔹 Check if the transaction has files 🔹
        hist_check_cmd = f"accurev hist -s {stream_name} -t {txn['txn_id']}"
        hist_result = run_command(hist_check_cmd, exit_on_fail=False)

        if not hist_result or "no elements selected" in hist_result.lower():
            print(f"⚠️ Skipping Transaction {txn['txn_id']} (No files in this transaction).")
            continue  # Move to next transaction

        # Populate workspace with transaction state
        pop_result = run_command(f"accurev pop -t {txn['txn_id']} -R -O -L {target_dir}", exit_on_fail=False)

        if pop_result is None or "No elements selected" in pop_result:
            print(f"⚠️ Skipping Transaction {txn['txn_id']} (No files found).")
            continue

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

    # Step 7: Push to remote Git repository
    run_command(f"git push", cwd=git_repo_path)

    print(f"✅ Successfully migrated AccuRev stream '{stream_name}' history to Git.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AccuRev to Git Full Migration")
    parser.add_argument("stream_name", help="AccuRev stream to migrate")
    parser.add_argument("git_repo_path", help="Path to the target Git repository")
    
    args = parser.parse_args()
    migrate_accurev_to_git(args.stream_name, args.git_repo_path)

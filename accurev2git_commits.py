import os
import subprocess
import argparse
import datetime
import re

def run_command(command, cwd=None):
    """Executes a shell command and returns the output."""
    result = subprocess.run(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"❌ Error running command: {command}\n{result.stderr}")
        exit(1)
    return result.stdout.strip()

def accurev_login():
    """Ensures the user is logged into AccuRev to avoid session expiration."""
    print("🔄 Logging into AccuRev...")
    run_command("accurev login jp_adm AccPass123")  # Change credentials accordingly

def parse_accurev_history(history_output):
    """Parses the text-based AccuRev history output."""
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

    # Step 3: Initialize Git if not already initialized
    if not os.path.exists(os.path.join(git_repo_path, ".git")):
        run_command(f"git init", cwd=git_repo_path)

    # Step 4: Get AccuRev transaction history
    transactions = get_accurev_history(stream_name)

    # Step 5: Apply each AccuRev version as a Git commit
    for txn in transactions:
        print(f"🚀 Processing Transaction: {txn['txn_id']} by {txn['user']} on {txn['date']}")

        # Populate workspace with transaction state
        run_command(f"accurev pop -t {txn['txn_id']} -R -O -v {stream_name} -L {target_dir}")

        # Add files to Git
        run_command(f"git add .", cwd=git_repo_path)

        # Commit with original author and timestamp
        commit_cmd = (
            f'GIT_COMMITTER_DATE="{txn["date"]}" GIT_AUTHOR_DATE="{txn["date"]}" '
            f'git commit --author="{txn["user"]} <{txn["user"]}@accurev.com>" --date="{txn["date"]}" '
            f'-m "{txn["message"]}"'
        )
        run_command(commit_cmd, cwd=git_repo_path)

    # Step 6: Push to remote Git repository
    run_command(f"git push origin master", cwd=git_repo_path)

    print(f"✅ Successfully migrated AccuRev stream '{stream_name}' history to Git.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AccuRev to Git Full Migration")
    parser.add_argument("stream_name", help="AccuRev stream to migrate")
    parser.add_argument("git_repo_path", help="Path to the target Git repository")
    
    args = parser.parse_args()
    migrate_accurev_to_git(args.stream_name, args.git_repo_path)

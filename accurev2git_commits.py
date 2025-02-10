import os
import subprocess
import argparse
import datetime

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

def get_accurev_history(stream_name):
    """Retrieves AccuRev transaction history for a given stream."""
    print("📜 Fetching AccuRev history...")
    history_cmd = f"accurev hist -s {stream_name} -fx"
    history_output = run_command(history_cmd)

    transactions = []
    for line in history_output.split("\n"):
        if "transaction id=" in line:
            txn_id = line.split('"')[1]
        if "<user>" in line:
            user = line.split(">")[1].split("<")[0]
        if "<time>" in line:
            date_str = line.split(">")[1].split("<")[0]
            transactions.append((txn_id, user, date_str))
    
    return transactions[::-1]  # Reverse to apply oldest commits first

def migrate_accurev_to_git(stream_name, git_repo_path):
    """Migrates AccuRev stream history into a Git repository."""
    
    # Step 1: Log into AccuRev (avoids expired session errors)
    accurev_login()

    # Step 2: Create a new unique workspace (avoid conflicts)
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
    for txn_id, user, date_str in transactions:
        print(f"🚀 Processing Transaction: {txn_id} by {user} on {date_str}")

        # Populate workspace with transaction state
        run_command(f"accurev pop -t {txn_id} -R -O -v {stream_name} -L {target_dir}")

        # Add files to Git
        run_command(f"git add .", cwd=git_repo_path)

        # Commit with original author and timestamp
        commit_cmd = (
            f'GIT_COMMITTER_DATE="{date_str}" GIT_AUTHOR_DATE="{date_str}" '
            f'git commit --author="{user} <{user}@accurev.com>" --date="{date_str}" '
            f'-m "AccuRev Transaction {txn_id}"'
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

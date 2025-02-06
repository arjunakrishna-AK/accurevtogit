import os
import subprocess
import argparse
import datetime

def run_command(command, cwd=None):
    """Executes a shell command and returns the output."""
    result = subprocess.run(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"Error running command: {command}\n{result.stderr}")
        exit(1)
    return result.stdout.strip()

def accurev_login():
    """Ensures the user is logged into AccuRev to avoid session token expiration issues."""
    print("🔄 Logging into AccuRev...")
    run_command("accurev login jp_adm AccPass123")

def check_existing_workspace(workspace_name):
    """Checks if a workspace already exists in AccuRev."""
    result = run_command("accurev show -fx wspaces")
    return workspace_name in result

def migrate_accurev_stream(stream_name, git_repo_path):
    """Migrates an AccuRev stream to a Git repository as a folder."""
    
    # Step 1: Log into AccuRev (avoids expired session errors)
    accurev_login()

    # Step 2: Create target directory if it doesn't exist
    target_dir = os.path.join(git_repo_path, stream_name)
    os.makedirs(target_dir, exist_ok=True)

    # Step 3: Check if workspace exists
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    workspace_name = f"accurev_{stream_name}_ws_{timestamp}"
    
    if not check_existing_workspace(workspace_name):
        print(f"Creating new workspace: {workspace_name}")
        run_command(f"accurev mkws -w {workspace_name} -b {stream_name} -l {target_dir}")
    else:
        print(f"✅ Using existing workspace: {workspace_name}")

    # Step 4: Update AccuRev workspace
    run_command(f"accurev update", cwd=target_dir)

    # Step 5: Initialize Git repo if not already initialized
    if not os.path.exists(os.path.join(git_repo_path, ".git")):
        run_command(f"git init", cwd=git_repo_path)

    # Step 6: Add files to Git
    run_command(f"git add {stream_name}", cwd=git_repo_path)
    run_command(f'git commit -m "Migrated AccuRev stream {stream_name}"', cwd=git_repo_path)

    print(f"✅ Successfully migrated AccuRev stream '{stream_name}' to Git.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AccuRev to Git Migration")
    parser.add_argument("stream_name", help="AccuRev stream to migrate")
    parser.add_argument("git_repo_path", help="Path to the target Git repository")
    
    args = parser.parse_args()
    migrate_accurev_stream(args.stream_name, args.git_repo_path)

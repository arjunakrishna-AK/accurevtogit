import os
import subprocess
import argparse

def run_command(command, cwd=None):
    """Executes a shell command and returns the output."""
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {command}\n{result.stderr}")
        exit(1)
    return result.stdout.strip()

def migrate_accurev_stream(stream_name, git_repo_path):
    """Migrates an AccuRev stream to a Git repository as a folder."""
    
    # Step 1: Create target directory
    target_dir = os.path.join(git_repo_path, stream_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # Step 2: Synchronize AccuRev workspace with the specified stream
    workspace_name = f"accurev_{stream_name}_ws"
    run_command(f"accurev mkws -w {workspace_name} -b {stream_name} -l {target_dir}")
    run_command(f"accurev co -R {target_dir}")
    run_command(f"accurev update", cwd=target_dir)

    # Step 3: Initialize Git repo if not already initialized
    if not os.path.exists(os.path.join(git_repo_path, ".git")):
        run_command(f"git init", cwd=git_repo_path)

    # Step 4: Add files to Git
    run_command(f"git add {stream_name}", cwd=git_repo_path)
    run_command(f'git commit -m "Migrated AccuRev stream {stream_name}"', cwd=git_repo_path)

    print(f"✅ Successfully migrated AccuRev stream '{stream_name}' to Git.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AccuRev to Git Migration")
    parser.add_argument("stream_name", help="AccuRev stream to migrate")
    parser.add_argument("git_repo_path", help="Path to the target Git repository")
    
    args = parser.parse_args()
    migrate_accurev_stream(args.stream_name, args.git_repo_path)

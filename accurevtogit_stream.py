import os
import subprocess
import datetime

# Configuration
TEMP_DIR = "/home/parekjx6/accurevtogit/devaccgit"  # Temporary directory for migration
SELECTED_STREAMS = ["adminshare"]  # List of AccuRev streams to migrate


def run_command(command, cwd=None):
    """Execute a shell command and return its output."""
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {command}\n{result.stderr}")
        exit(1)
    return result.stdout.strip()



def migrate_stream(stream_name):
    """Migrate a specific AccuRev stream to Git."""
    print(f"\nStarting migration for AccuRev stream: {stream_name}")

    # Set AccuRev workspace
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    workspace = f"accurev_{stream_name}_ws_{timestamp}"
    run_command(f"accurev mkws -w {workspace} -b {stream_name} -l {TEMP_DIR}")
    run_command(f"accurev update", cwd=TEMP_DIR)

    # Fetch AccuRev history
    history_output = run_command(f"accurev hist -s {stream_name} -t now.1000")

    # Convert AccuRev history to Git commits

    for entry in history_output.split("<transaction "):
        if "id=" not in entry:
            continue
        try:
            trans_id = entry.split('id="')[1].split('"')[0]
            user = entry.split('principal="')[1].split('"')[0]
            time = entry.split('time="')[1].split('"')[0]
            comment = entry.split('comment="')[1].split('"')[0]

            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

            # Synchronize to the transaction
            run_command(f"accurev update -t {trans_id}", cwd=TEMP_DIR)
            run_command(f"git add .", cwd=TEMP_DIR)
            run_command(f'git commit -m "{comment}" --author="{user} <{user}@yourcompany.com>" --date="{timestamp}"', cwd=TEMP_DIR)

        except Exception as e:
            print(f"Error processing transaction {trans_id}: {e}")

    # Push to GitHub
    run_command(f"git branch develop", cwd=TEMP_DIR)
    run_command(f"git push", cwd=TEMP_DIR)

    print(f"Successfully migrated {stream_name} to GitHub!")


# Run migration for selected streams
for stream in SELECTED_STREAMS:
    migrate_stream(stream)

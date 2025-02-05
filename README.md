# accurevtogit

Run the Script

Navigate to the script's directory and run:

python accurev_to_git.py feature_branch_1 /home/user/git_repo



What Happens Internally?

Checks and creates a folder inside Git repo:

→ /home/user/git_repo/feature_branch_1

1.Creates an AccuRev workspace for the stream.

2.Syncs the stream’s files into the folder.

3.Initializes Git if not already initialized.

4.Adds the folder to Git and commits the changes.

5.Final message confirming success.


Verify the Migration

Check inside the Git repository:

ls /home/user/git_repo/




To verify Git history:

cd /home/user/git_repo/

git log --oneline



Push to Remote Repository:

If you want to push this to a remote Git repository (e.g., GitHub, GitLab):

cd /home/user/git_repo

git remote add origin <your-git-repo-url>

git push origin main



import os
import shutil
import sqlite3
import subprocess
import stat
from pathlib import Path

def run_cmd(args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def remove_readonly(func, path, excinfo):
    # Clears the readonly bit and re-attempts the removal
    os.chmod(path, stat.S_IWRITE)
    func(path)

def safe_rmtree(path):
    if path.exists():
        shutil.rmtree(path, onerror=remove_readonly)

def main():
    scratch_dir = Path(r"C:\Users\user2\.gemini\antigravity\scratch")
    temp_init_dir = scratch_dir / "tmp-init-git"
    bare_git_path = scratch_dir / "unity-game.git"
    workspace_path = scratch_dir / "unity-game-workspace"

    # Cleanup any old runs
    safe_rmtree(temp_init_dir)
    safe_rmtree(bare_git_path)
    safe_rmtree(workspace_path)

    # Initialize bare repo with a main branch and initial commit
    print("Initializing initial git repository...")
    temp_init_dir.mkdir(parents=True, exist_ok=True)
    run_cmd(["git", "init", "-b", "main"], cwd=temp_init_dir)
    
    # Configure local git identity for setup commit
    run_cmd(["git", "config", "user.email", "ai-game-company@example.local"], cwd=temp_init_dir)
    run_cmd(["git", "config", "user.name", "AI Game Company Setup"], cwd=temp_init_dir)

    readme_file = temp_init_dir / "README.md"
    readme_file.write_text("# Maldhalla-class Game\n\nInitial Unity project repository.\n", encoding="utf-8")

    run_cmd(["git", "add", "README.md"], cwd=temp_init_dir)
    run_cmd(["git", "commit", "-m", "Initial commit"], cwd=temp_init_dir)

    print(f"Creating bare git repository at {bare_git_path}...")
    run_cmd(["git", "clone", "--bare", str(temp_init_dir), str(bare_git_path)])

    # Clean up temp
    safe_rmtree(temp_init_dir)

    # Update database
    print("Updating project repository settings in database...")
    db_path = scratch_dir / "ai-game-company-server" / "data" / "game_company.sqlite3"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE projects SET repo_url = ?, workspace_path = ?, engine = ? WHERE id = 1",
        (bare_git_path.as_posix(), workspace_path.as_posix(), "unity")
    )
    conn.commit()
    conn.close()
    print("Seeding/setup completed successfully!")

if __name__ == "__main__":
    main()

import os
from pathlib import Path

def main():
    print("Creating initial Unity repository skeleton...")
    
    # 1. Create directories
    for folder in ["Assets", "Packages", "ProjectSettings"]:
        Path(folder).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {folder}/")

    # 2. Create basic .gitignore for Unity
    gitignore_content = """# Unity default gitignore
/[Ll]ibrary/
/[Tt]emp/
/[Oo]bj/
/[Bb]uild/
/[Bb]uilds/
/[Ll]ogs/
/[Uu]ser[Ss]ettings/
MemoryCaptures/
Recording/

# Asset Meta files
/[Aa]ssets/*.meta

# OS generated
.DS_Store
Thumbs.db
"""
    Path(".gitignore").write_text(gitignore_content, encoding="utf-8")
    print("Created: .gitignore")

    # 3. Create Packages/manifest.json
    manifest_content = """{
  "dependencies": {
    "com.unity.modules.ui": "1.0.0",
    "com.unity.modules.imgui": "1.0.0"
  }
}
"""
    Path("Packages/manifest.json").write_text(manifest_content, encoding="utf-8")
    print("Created: Packages/manifest.json")

    # 4. Create a README updater or project README
    readme_content = """# Maldhalla-class Game

This is the initial Unity project repository skeleton.

## Folder Structure
- `Assets/`: Game assets, scripts, and scenes.
- `Packages/`: Project package dependencies.
- `ProjectSettings/`: Unity editor settings.
"""
    Path("README.md").write_text(readme_content, encoding="utf-8")
    print("Created: README.md")
    
    print("Unity skeleton creation completed successfully!")

if __name__ == "__main__":
    main()

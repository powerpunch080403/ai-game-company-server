#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-$HOME/game-repos/demo-game.git}"
seed_dir="$(mktemp -d)"

cleanup() {
  rm -rf "$seed_dir"
}
trap cleanup EXIT

mkdir -p "$(dirname "$repo_root")"

if [ -d "$repo_root" ]; then
  echo "Demo repo already exists: $repo_root"
  exit 0
fi

git init --bare "$repo_root"
git -C "$repo_root" symbolic-ref HEAD refs/heads/main

git init -b main "$seed_dir"
git -C "$seed_dir" config user.email "ai-game-company@example.local"
git -C "$seed_dir" config user.name "AI Game Company"

cat > "$seed_dir/README.md" <<'EOF'
# Demo Game

Temporary engine-agnostic game repository for AI Game Company workflow tests.
EOF

mkdir -p "$seed_dir/docs"
cat > "$seed_dir/docs/project.md" <<'EOF'
# Project Notes

Engine: undecided
Purpose: verify worker branch preparation before real game development starts.
EOF

git -C "$seed_dir" add README.md docs/project.md
git -C "$seed_dir" commit -m "Initial demo game project"
git -C "$seed_dir" remote add origin "$repo_root"
git -C "$seed_dir" push -u origin main

echo "Demo repo created: $repo_root"

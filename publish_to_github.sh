#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: ./publish_to_github.sh <github-repository-url>"
  exit 1
fi

REPO_URL="$1"

git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
git push -u origin main

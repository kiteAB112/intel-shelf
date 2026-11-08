#!/bin/bash
# Commit only maintained project files after tests; retry previously committed pushes too.
set -eu
cd "$HOME/intel-shelf"
exec 9>.maintenance.lock
flock -n 9
python3 -m unittest discover -s tests -q
python3 scripts/maintain.py --render-only
mapfile -t files < <(git ls-files --cached --others --exclude-standard -- sources scripts tests data/status.json data/review-queue.json data/maintenance-tasks.json data/feedback.json DIRECTORY.md index.html | sort -u)
git add -- "${files[@]}"
if ! git diff --quiet HEAD -- "${files[@]}"; then
    git commit --quiet --only -m "Apply validated Hermes source maintenance updates" -- "${files[@]}"
fi
git push origin HEAD:main
git rev-parse HEAD

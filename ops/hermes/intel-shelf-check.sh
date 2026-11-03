#!/bin/bash
set -eu
cd "$HOME/intel-shelf"
exec 9>.maintenance.lock
flock -n 9
git pull --ff-only --quiet
export INTEL_SHELF_ORIGIN=hermes-cloud
python3 scripts/maintain.py > data/latest-check.log
files=(data/status.json data/review-queue.json data/maintenance-tasks.json data/feedback.json DIRECTORY.md index.html)
if ! git diff --quiet HEAD -- "${files[@]}"; then
    git commit --quiet --only -m "Refresh Hermes source maintenance snapshot" -- "${files[@]}"
fi
git push --quiet origin HEAD:main

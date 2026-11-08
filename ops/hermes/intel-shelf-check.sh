#!/bin/bash
set -eu
cd "$HOME/intel-shelf"
exec 9>.maintenance.lock
flock -n 9
git pull --ff-only --quiet
export INTEL_SHELF_ORIGIN=hermes-cloud
python3 scripts/maintain.py > data/latest-check.log
# Release the check lock before invoking the publisher that uses the same lock.
flock -u 9
bash ops/hermes/intel-shelf-publish.sh >> data/latest-check.log 2>&1

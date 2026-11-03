#!/bin/bash
set -eu
cd "$HOME/intel-shelf"
export INTEL_SHELF_ORIGIN=hermes-cloud
flock -n .maintenance.lock python3 scripts/maintain.py > data/latest-check.log

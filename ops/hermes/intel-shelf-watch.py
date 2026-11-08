"""Stable repair triggers, renewed after three more failed checks."""
import json
from pathlib import Path

root = Path.home() / "intel-shelf"
tasks = json.loads((root / "data/maintenance-tasks.json").read_text())["tasks"]
print(json.dumps(sorted((t["source_id"], sorted(t["reasons"]), t.get("action", "review"),
                         t.get("consecutive_problem_checks", 0) // 3)
                        for t in tasks)))

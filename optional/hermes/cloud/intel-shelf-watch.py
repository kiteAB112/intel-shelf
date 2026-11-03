import json
from pathlib import Path

root = Path.home() / "intel-shelf"
tasks = json.loads((root / "data/maintenance-tasks.json").read_text())["tasks"]
print(json.dumps(sorted((t["source_id"], sorted(t["reasons"])) for t in tasks)))

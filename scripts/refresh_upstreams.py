"""Refresh public upstream metadata; dependency-free, no cloning or tokens committed.

Only repository metadata and the latest commit SHA are requested.
A missing/failed upstream is recorded as error, never fabricated.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
catalog = json.loads((ROOT / "catalog/upstreams.json").read_text(encoding="utf-8"))
token = os.environ.get("GITHUB_TOKEN", "")
results = {}
now = datetime.now(timezone.utc).isoformat()
for name in catalog["repositories"]:
    req = urllib.request.Request("https://api.github.com/repos/" + name, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "SimWhy-Upstream-Tracker",
        **({"Authorization": "Bearer " + token} if token else {})
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            entry = json.load(response)
        results[name] = {
            "url": entry["html_url"],
            "default_branch": entry["default_branch"],
            "latest_push_utc": entry.get("pushed_at"),
            "stars": entry.get("stargazers_count"),
            "open_issues": entry.get("open_issues_count"),
            "archived": entry.get("archived", False)
        }
        print(f"OK {name} stars={results[name]['stars']}")
    except (urllib.error.URLError, ValueError, KeyError, TimeoutError) as exc:
        results[name] = {"error": type(exc).__name__ + ": " + str(exc)}
        print(f"ERROR {name}: {exc}", file=sys.stderr)

output = {"checked_at_utc": now, "metadata_only": True, "repositories": results}
dest = ROOT / "catalog/upstream_status.json"
dest.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
failures = sum(1 for data in results.values() if "error" in data)
print(f"Tracked {len(results)} repositories; failures={failures}; output={dest}")
if failures:
    sys.exit(1)

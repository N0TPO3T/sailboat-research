#!/usr/bin/env python3
"""Compare upstream with the pre-migration inventory without modifying upstream."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "sailboat-research"
sys.dont_write_bytecode = True


def main():
    before = json.loads((ROOT / "runs/audit/upstream_files_before.json").read_text())
    current = {}
    for root, dirs, files in os.walk(SOURCE, followlinks=False):
        dirs[:] = [d for d in dirs if d not in (".git", ".venv", "__pycache__")]
        for name in files:
            path = Path(root) / name
            relative = path.relative_to(SOURCE).as_posix()
            if path.is_symlink():
                current[relative] = {"symlink": os.readlink(path)}
            else:
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                current[relative] = {"sha256": digest, "bytes": path.stat().st_size}
    changed = sorted(k for k in before.keys() & current.keys() if before[k] != current[k])
    status = subprocess.check_output(["git", "--no-optional-locks", "-C", str(SOURCE),
                                      "status", "--porcelain=v1", "-z"])
    result = {"source_root": str(SOURCE), "files": len(current), "changed": changed,
              "added": sorted(current.keys()-before.keys()), "removed": sorted(before.keys()-current.keys()),
              "git_status_unchanged": status == (ROOT / "runs/audit/upstream_git_status_before.bin").read_bytes(),
              "excluded_trees": [".git", ".venv", "__pycache__"]}
    result["passed"] = not (result["changed"] or result["added"] or result["removed"]) and result["git_status_unchanged"]
    (ROOT / "runs/audit/upstream_integrity.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

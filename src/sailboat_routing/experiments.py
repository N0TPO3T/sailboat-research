"""Serial CPU experiment accounting shared by the gated development runners."""
import json
import time
from .runtime import ROOT


class Budget:
    def __init__(self, command, seconds=3600):
        self.path = ROOT / "runs/computation.jsonl"
        self.command = command
        self.limit = seconds
        self.used = sum(json.loads(line)["wall_seconds"] for line in self.path.read_text().splitlines()) if self.path.exists() else 0.0
        self.started = time.monotonic()

    def check(self):
        if self.used + time.monotonic() - self.started >= self.limit:
            raise TimeoutError("Cumulative V0 development compute budget exhausted")

    def finish(self, status):
        with self.path.open("a") as stream:
            stream.write(json.dumps({"command": self.command, "wall_seconds": time.monotonic()-self.started, "status": status})+"\n")


def output_directory(name):
    from pathlib import Path
    if Path(name).name != name or name in (".", ".."):
        raise ValueError("Output must be a single new directory name under runs")
    path = ROOT / "runs" / name
    path.mkdir(exist_ok=False)
    return path

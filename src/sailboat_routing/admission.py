"""Evidence-bound development admission, separate from measured task success rates."""
from pathlib import Path
import hashlib
import json
from .runtime import ROOT

REQUIRED_CHECKS = ("matched_assets", "migration_parity", "finite_dynamics",
                   "continuous_physics", "causal_memory", "feature_noninterference",
                   "navigation_demonstrated")


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inside(path):
    path = Path(path)
    path = path if path.is_absolute() else ROOT / path
    path = path.resolve(strict=True)
    if not path.is_relative_to(ROOT):
        raise ValueError("Runtime/evidence path must remain inside NEW_ROOT")
    return path


def definition_hash(definition):
    return hashlib.sha256(json.dumps(definition, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_admission(path=None):
    path = inside(path or ROOT / "runs/navigation_admission.json")
    record = json.loads(path.read_text())
    if record.get("schema") != 2 or record.get("eligible_for_development") is not True:
        raise ValueError("Development admission is missing or declined")
    checks = record.get("checks", {})
    if any(checks.get(key) is not True for key in REQUIRED_CHECKS):
        raise ValueError("A required interface/behavior admission check is not satisfied")
    definition = record["protocol"]
    identity = record["source_identity"]
    if definition_hash(definition) != identity["protocol_sha256"]:
        raise ValueError("Protocol definition differs from approved identity")
    for name, expected in definition["source_files"].items():
        if file_hash(inside(name)) != expected:
            raise ValueError(f"Approved protocol source changed: {name}")
    for kind in ("actor", "normalizer"):
        if file_hash(inside(definition[kind])) != identity[kind+"_sha256"]:
            raise ValueError(f"Approved {kind} asset changed")
    if definition["feature_schema"] != identity["feature_schema"]:
        raise ValueError("Feature schema does not match approved protocol")
    for evidence in record["evidence"]:
        if file_hash(inside(evidence["path"])) != evidence["sha256"]:
            raise ValueError("Admission evidence changed; do not silently relabel old outcomes")
    return record

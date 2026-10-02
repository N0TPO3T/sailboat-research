#!/usr/bin/env python3
"""Inspect the supplied 0204 obstacle candidate without changing the frozen V0 policy."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import hashlib
import importlib.util
import json
import shutil
import torch

SOURCE = ROOT.parent / "sailboat-research"
ASSETS = SOURCE / "research/weights_library/20260928_import/01_obstacle_18d/user_0204_10800"
EXPECTED = {
    "saclstm_s14obst_noise_0204_actor10800.pth": "6092d4543c003793f4cd3f21c5ed722f0978eebfdba2f62d77892af333085bd6",
    "saclstm_s14obst_noise_0204_normalizer10800.pth": "3baf7d1d9d4c9e4505fc991f339221e9e0dc64e9777c6f1c568413a2846b63b6",
    "saclstm_s14obst_noise_0204_q_critic10800.pth": "577a6abd82ba4c7cb2408fae51f00f92c7df8e7ceab70ba716051da5f542ab0d",
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    out = ROOT / "runs/asset_0204_review"
    out.mkdir(exist_ok=False)
    snapshot = out / "snapshot"; snapshot.mkdir()
    manifest = []
    for filename, expected in EXPECTED.items():
        path = ASSETS / filename
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"Server candidate differs from user ZIP: {filename}")
        shutil.copyfile(path, snapshot / filename)
        manifest.append({"source": str(path), "target": str(snapshot / filename), "sha256": digest})
    ref = SOURCE / "sailboat_RL/PART5/SAC-LSTM-att"
    for filename in ("globals.py", "utils_lstm_att_normal.py", "modeltest_noise.py", "batchtest.py"):
        path = ref / filename
        shutil.copyfile(path, snapshot / filename)
        manifest.append({"source": str(path), "target": str(snapshot / filename), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    previous = sys.modules.get("globals")
    sys.modules["globals"] = load("candidate_globals", snapshot / "globals.py")
    try:
        network = load("candidate_network", snapshot / "utils_lstm_att_normal.py")
    finally:
        if previous is None: sys.modules.pop("globals", None)
        else: sys.modules["globals"] = previous
    actor_state = torch.load(snapshot / "saclstm_s14obst_noise_0204_actor10800.pth", map_location="cpu", weights_only=True)
    critic_state = torch.load(snapshot / "saclstm_s14obst_noise_0204_q_critic10800.pth", map_location="cpu", weights_only=True)
    stats = torch.load(snapshot / "saclstm_s14obst_noise_0204_normalizer10800.pth", map_location="cpu", weights_only=True)
    for state in (actor_state, critic_state, stats):
        if not all(torch.isfinite(v).all() for v in state.values() if torch.is_tensor(v)):
            raise ValueError("Non-finite checkpoint values")
    actor = network.Actor(18, 2, (256, 256)).eval().requires_grad_(False)
    critic = network.Double_Q_Critic(18, 2, (256, 256), (256, 128)).eval().requires_grad_(False)
    actor.load_state_dict(actor_state, strict=True); critic.load_state_dict(critic_state, strict=True)
    normalizer = network.ZScoreNormalizer(18, torch.device("cpu"))
    if stats["mean"].shape != (18,) or stats["var"].shape != (18,) or (stats["var"] < 0).any() or stats["count"] <= 0:
        raise ValueError("Invalid matching normalizer")
    normalizer.load_state_dict(stats)
    with torch.inference_mode():
        current = normalizer.normalize(stats["mean"].unsqueeze(0))
        sequence_action, _ = actor(current_state=current, state_sequence=current.unsqueeze(1).repeat(1, 10, 1),
            action_sequence=torch.zeros(1, 10, 2), deterministic=True)
        actor.reset_hidden_state()
        previous_action = torch.zeros(1, 2)
        for _ in range(12):
            streamed, _ = actor(current_state=current, prev_state=current, prev_action=previous_action,
                deterministic=True, single_step_mode=True, env_ids=["inspection"])
            previous_action = streamed
            if not torch.isfinite(streamed).all(): raise ValueError("Non-finite structural probe")
    result = {
        "user_zip_sha256": "f3d8f7c0c715fc6e2c312f8ba7656c9f8e0b726a598279bb071e03c8d561c73f",
        "same_as_preexisting_library": True, "obs_dim": 18, "action_dim": 2,
        "architecture": "SAC-LSTM with scaled-dot-product history attention",
        "actor_and_critic_strict_load": True, "normalizer_count": int(stats["count"]),
        "normalizer_mean": stats["mean"].tolist(), "normalizer_var": stats["var"].tolist(),
        "synthetic_eval_mode_sequence_action": sequence_action.tolist(),
        "synthetic_eval_mode_streaming_action": streamed.tolist(),
        "source_default_history_window": actor.history_window_size,
        "source_entry_evidence": {"modeltest_noise.py": {"env_name": "sailboat-s14-obst-v3", "prefix": "saclstm_s14obst_noise_0204", "checkpoint": 10800, "sensor_noise": 0.03, "actuator_noise": 0.03},
                                  "batchtest.py": {"same_prefix_checkpoint_and_env": True}},
        "manifest": manifest,
        "limits": ["This is structural compatibility, not a navigation or avoidance rollout",
                   "No original evaluator was launched; its output paths and multi-process default are not used",
                   "Eval mode here is explicit for this probe; legacy entry dropout/RNG behavior still needs fidelity audit",
                   "Not interchangeable with the frozen 14D V0 controller or its causal feature schema",
                   "V2/V3 observation meanings, attention history and environment registration must be bound before performance use",
                   "Current V0 checkpoint, normalizer, low-level code and Stage B failure evidence are unchanged"]}
    (out / "inspection.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

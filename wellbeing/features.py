"""Feature encoding shared by training and inference.

The model is a single regressor over (check-in context + one-hot scene) that predicts
the wellbeing gain of running that scene now. Inference scores every scene by building
one row per candidate scene.
"""
import pandas as pd

from .catalog import PHASE_KEYS, SCENE_KEYS, TIME_BLOCK_KEYS

CONTEXT_NUMERIC = ("mood", "energy", "stress", "homesickness", "sleep_hours")
FEATURE_COLUMNS = (
    *CONTEXT_NUMERIC,
    *(f"phase_{key}" for key in PHASE_KEYS),
    *(f"time_{key}" for key in TIME_BLOCK_KEYS),
    *(f"scene_{key}" for key in SCENE_KEYS),
)

# Typical values used as the "reference person" in explanations.
REFERENCE_CONTEXT = {
    "mood": 3, "energy": 3, "stress": 2, "homesickness": 2, "sleep_hours": 7.0,
    "mission_phase": "routine", "time_block": "evening",
}
CONTEXT_GROUPS = ("mood", "energy", "stress", "homesickness", "sleep_hours", "mission_phase", "time_block")


def encode(contexts: pd.DataFrame, scenes) -> pd.DataFrame:
    """Encode contexts (one row each) paired with the scene in `scenes` (same length)."""
    out = pd.DataFrame(index=contexts.index)
    for column in CONTEXT_NUMERIC:
        out[column] = contexts[column].astype(float)
    for key in PHASE_KEYS:
        out[f"phase_{key}"] = (contexts["mission_phase"] == key).astype(float)
    for key in TIME_BLOCK_KEYS:
        out[f"time_{key}"] = (contexts["time_block"] == key).astype(float)
    scenes = pd.Series(list(scenes), index=contexts.index)
    for key in SCENE_KEYS:
        out[f"scene_{key}"] = (scenes == key).astype(float)
    return out.loc[:, list(FEATURE_COLUMNS)]


def encode_all_scenes(context: dict) -> pd.DataFrame:
    """One encoded row per scene for a single check-in context."""
    frame = pd.DataFrame([context] * len(SCENE_KEYS))
    return encode(frame, SCENE_KEYS)

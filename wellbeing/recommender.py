"""Adaptive engine: check-in context → ranked VR scenes.

Two layers:

1. Population model (trained offline, see training.py) predicts the wellbeing gain of
   each scene for this context.
2. Personal layer (contextual bandit). For each scene we keep a Bayesian estimate of how
   much this astronaut's real re-check gains differ from the population prediction
   (their residuals). Thompson sampling draws from that estimate, so scenes with little
   personal evidence are occasionally tried, and scenes that consistently over- or
   under-perform for this person move up or down. This is the "re-check learns what
   works" loop: every completed re-check adds one residual.

Safety rules (catalog.ELIGIBILITY_RULES) remove scenes before ranking.
"""
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from .catalog import SCENE_KEYS, SCENES_BY_KEY, blocked_reason
from .features import CONTEXT_GROUPS, REFERENCE_CONTEXT, encode_all_scenes

PRIOR_SD = 0.35  # how far one astronaut's taste may plausibly differ from the population
DEFAULT_RESIDUAL_SD = 0.9


class ModelUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=4)
def _load(path: str, mtime: float):
    import joblib

    bundle = joblib.load(path)
    if tuple(bundle["scenes"]) != SCENE_KEYS:
        raise ModelUnavailable("The saved model was trained on a different scene catalogue. Retrain it.")
    return bundle


def load_bundle(path) -> dict:
    path = Path(path)
    if not path.exists():
        raise ModelUnavailable(
            "No trained recommender found. Run: python manage.py generate_wellbeing_data && python manage.py train_recommender"
        )
    return _load(str(path), path.stat().st_mtime)


def predict_gains(bundle: dict, context: dict) -> dict:
    rows = encode_all_scenes(context)
    predictions = bundle["model"].predict(rows)
    return {key: float(value) for key, value in zip(SCENE_KEYS, predictions)}


@dataclass
class Personal:
    mean: float = 0.0
    sd: float = PRIOR_SD
    sessions: int = 0


def personal_adjustments(history, residual_sd: float = DEFAULT_RESIDUAL_SD) -> dict:
    """Normal–normal posterior of each scene's personal offset from (scene, residual) pairs."""
    sums = {key: 0.0 for key in SCENE_KEYS}
    counts = {key: 0 for key in SCENE_KEYS}
    for scene, residual in history:
        if scene in sums:
            sums[scene] += residual
            counts[scene] += 1
    result = {}
    for key in SCENE_KEYS:
        precision = 1 / PRIOR_SD**2 + counts[key] / residual_sd**2
        mean = (sums[key] / residual_sd**2) / precision
        result[key] = Personal(mean=mean, sd=math.sqrt(1 / precision), sessions=counts[key])
    return result


@dataclass
class RankedScene:
    key: str
    predicted: float  # population model
    adjustment: float  # personal posterior mean
    uncertainty: float  # personal posterior sd
    sessions: int
    score: float  # value used for the choice (includes the Thompson draw)
    blocked: str | None = None

    @property
    def expected(self) -> float:
        return self.predicted + self.adjustment

    @property
    def scene(self):
        return SCENES_BY_KEY[self.key]

    def as_dict(self) -> dict:
        return {
            "key": self.key, "predicted": round(self.predicted, 3), "adjustment": round(self.adjustment, 3),
            "uncertainty": round(self.uncertainty, 3), "sessions": self.sessions,
            "score": round(self.score, 3), "blocked": self.blocked,
        }


@dataclass
class Recommendation:
    ranked: list
    recommended: str
    exploring: bool
    duration: int
    reasons: list = field(default_factory=list)
    model_version: str = ""


def rank_scenes(predictions: dict, personal: dict, context: dict, rng=None, explore: bool = True) -> list:
    rng = rng or np.random.default_rng()
    ranked = []
    for key in SCENE_KEYS:
        info = personal[key]
        draw = rng.normal(info.mean, info.sd) if explore else info.mean
        ranked.append(RankedScene(
            key=key, predicted=predictions[key], adjustment=info.mean, uncertainty=info.sd,
            sessions=info.sessions, score=predictions[key] + draw, blocked=blocked_reason(key, context),
        ))
    ranked.sort(key=lambda item: (item.blocked is not None, -item.score))
    return ranked


def recommend_duration(scene_key: str, context: dict) -> int:
    """Session length rule (10–30 min). Prototype heuristic, not learned."""
    minutes = 20
    if context["time_block"] == "work":
        minutes = 10  # a break between tasks
    elif SCENES_BY_KEY[scene_key].arousal == "low" and context["stress"] >= 4:
        minutes = 25  # longer down-regulation for high stress
    if context["energy"] <= 2 or context["time_block"] == "pre_sleep":
        minutes = min(minutes, 15)
    return minutes


GROUP_LABELS = {
    "mood": lambda c: f"mood {c['mood']}/5",
    "energy": lambda c: f"energy {c['energy']}/5",
    "stress": lambda c: f"stress {c['stress']}/5",
    "homesickness": lambda c: f"missing home {c['homesickness']}/5",
    "sleep_hours": lambda c: f"{c['sleep_hours']:g} h sleep",
    "mission_phase": lambda c: {"adaptation": "early adaptation phase", "routine": "mid-mission phase", "late": "late mission phase"}[c["mission_phase"]],
    "time_block": lambda c: {"morning": "morning", "work": "work-day break", "evening": "evening", "pre_sleep": "pre-sleep wind-down"}[c["time_block"]],
}


def explain(bundle: dict, context: dict, scene_key: str, limit: int = 3) -> list:
    """Counterfactual drivers: how much each part of today's check-in moves the
    predicted gain of `scene_key`, relative to a typical check-in."""
    index = SCENE_KEYS.index(scene_key)
    base = predict_gains(bundle, context)[scene_key]
    effects = []
    for group in CONTEXT_GROUPS:
        if context[group] == REFERENCE_CONTEXT[group]:
            continue
        changed = {**context, group: REFERENCE_CONTEXT[group]}
        delta = base - float(bundle["model"].predict(encode_all_scenes(changed))[index])
        effects.append((delta, group))
    effects.sort(key=lambda item: -abs(item[0]))
    reasons = []
    for delta, group in effects[:limit]:
        if abs(delta) < 0.05:
            continue
        direction = "raises" if delta > 0 else "lowers"
        reasons.append(f"Your {GROUP_LABELS[group](context)} {direction} the predicted benefit by {abs(delta):.1f}.")
    return reasons


def recommend(bundle: dict, context: dict, history, rng=None, explore: bool = True) -> Recommendation:
    predictions = predict_gains(bundle, context)
    personal = personal_adjustments(history, bundle.get("residual_sd", DEFAULT_RESIDUAL_SD))
    ranked = rank_scenes(predictions, personal, context, rng=rng, explore=explore)
    eligible = [item for item in ranked if item.blocked is None]
    chosen = eligible[0]
    best_expected = max(eligible, key=lambda item: item.expected)
    reasons = explain(bundle, context, chosen.key)
    if chosen.sessions:
        reasons.append(
            f"From your {chosen.sessions} past re-check{'s' if chosen.sessions != 1 else ''} of this scene, "
            f"your personal adjustment is {chosen.adjustment:+.1f}."
        )
    exploring = chosen.key != best_expected.key
    if exploring:
        reasons.append(
            f"Exploring: {best_expected.scene.title} has a slightly higher expected benefit, but the engine is still "
            "learning how this scene works for you."
        )
    return Recommendation(
        ranked=ranked, recommended=chosen.key, exploring=exploring,
        duration=recommend_duration(chosen.key, context), reasons=reasons,
        model_version=bundle.get("version", ""),
    )

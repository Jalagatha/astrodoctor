"""Synthetic astronaut check-in → VR scene → re-check data.

No real dataset links astronaut mood to VR scene outcomes, so this module generates one
from explicit, documented assumptions (docs/WELLBEING_MODEL.md). It serves two purposes:

1. Training data for the population model (a randomised logging policy: every check-in
   is assigned a scene uniformly at random, as in a pilot study, so outcomes are unbiased).
2. A ground-truth "oracle" for evaluation. Each row carries `oracle_<scene>` columns with
   the expected gain of every scene for that astronaut and context (personal preference
   included, noise excluded). These columns are for evaluation only and are never model
   inputs.

All effect sizes below are prototype assumptions, not findings from spaceflight research.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .catalog import DURATION_CHOICES, SCENE_KEYS, TIME_BLOCK_KEYS, mission_phase, wellbeing_gain

TIME_BLOCK_WEIGHTS = (0.2, 0.25, 0.3, 0.25)
MOOD_NOISE_SD = 0.55
STRESS_NOISE_SD = 0.5
PERSONAL_EFFECT_SD = 0.35


def _clip(value, low, high):
    return float(min(high, max(low, value)))


def expected_effects(ctx: dict) -> dict:
    """Population-level expected (mood change, stress reduction) per scene for a context.

    `ctx` holds mood, energy, stress, homesickness (1–5), sleep_hours, mission_phase and
    time_block. Values are continuous; rounding to the 1–5 scales happens later.
    """
    low_mood = (3 - ctx["mood"]) / 2  # +1 very low … -1 great
    high_stress = (ctx["stress"] - 3) / 2
    low_energy = (3 - ctx["energy"]) / 2
    home = (ctx["homesickness"] - 3) / 2
    sleep_debt = _clip((7 - ctx["sleep_hours"]) / 3, -0.5, 1.5)
    pre_sleep = ctx["time_block"] == "pre_sleep"
    daytime = ctx["time_block"] in ("morning", "work")
    phase = ctx["mission_phase"]

    effects = {
        # Connection to home helps most when missing home; very homesick + very low mood
        # can deepen the sense of separation.
        "family": (
            0.3 + 0.55 * home + 0.25 * low_mood + 0.2 * (phase == "late") + 0.1 * (ctx["time_block"] == "evening")
            - 0.7 * (home >= 0.9 and low_mood >= 0.9),
            0.2 + 0.1 * home,
        ),
        # Restorative nature exposure: broadly good, best under stress and late in a long mission.
        "nature": (
            0.15 + 0.25 * high_stress + 0.15 * low_mood + 0.15 * (phase == "late"),
            0.45 + 0.35 * high_stress,
        ),
        # Learning engages a rested, energetic mind; it is a poor fit when tired or stressed.
        "learning": (
            0.3 - 0.35 * low_energy - 0.4 * max(sleep_debt, 0) - 0.3 * high_stress
            + 0.2 * daytime - 0.25 * pre_sleep,
            0.05 - 0.2 * high_stress,
        ),
        # Play lifts low mood if there is energy for it; it disrupts wind-down and early adaptation.
        "active": (
            0.35 + 0.35 * low_mood - 0.45 * max(low_energy, 0) + 0.35 * max(-low_energy, 0)
            + 0.2 * daytime - 0.6 * pre_sleep - 0.3 * max(sleep_debt, 0) - 0.3 * (phase == "adaptation"),
            0.3 + 0.25 * high_stress - 0.4 * pre_sleep,
        ),
        # Low-stimulation calm: for stress, tiredness and sleep preparation; dull when lively.
        "calm": (
            0.15 + 0.2 * high_stress + 0.25 * max(low_energy, 0) + 0.2 * max(sleep_debt, 0)
            + 0.35 * pre_sleep - 0.3 * max(-low_energy, 0) - 0.1 * daytime,
            0.5 + 0.4 * high_stress + 0.2 * pre_sleep,
        ),
    }
    return {key: (float(mood), float(stress)) for key, (mood, stress) in effects.items()}


def _apply_headroom(mood_change: float, mood: float) -> float:
    # Mood near the top of the scale has little room to rise (and vice versa).
    if mood_change >= 0:
        return mood_change * (0.4 + 0.6 * (5 - mood) / 4)
    return mood_change * (0.4 + 0.6 * (mood - 1) / 4)


def _apply_stress_headroom(reduction: float, stress: float) -> float:
    if reduction >= 0:
        return reduction * (0.3 + 0.7 * (stress - 1) / 4)
    return reduction * (0.3 + 0.7 * (5 - stress) / 4)


@dataclass
class Astronaut:
    astronaut_id: str
    base_mood: float
    base_energy: float
    base_stress: float
    base_home: float
    base_sleep: float
    personal: dict  # scene -> (mood offset, stress offset)


def make_astronaut(index: int, rng: np.random.Generator) -> Astronaut:
    personal = {}
    for key in SCENE_KEYS:
        offset = rng.normal(0, PERSONAL_EFFECT_SD)
        personal[key] = (offset, 0.5 * offset + rng.normal(0, 0.1))
    return Astronaut(
        astronaut_id=f"SYN-{index:03d}",
        base_mood=rng.normal(3.5, 0.4),
        base_energy=rng.normal(3.3, 0.4),
        base_stress=rng.normal(2.6, 0.4),
        base_home=rng.normal(2.3, 0.5),
        base_sleep=rng.normal(6.8, 0.45),
        personal=personal,
    )


def expected_gains(ctx: dict, astronaut: Astronaut | None = None) -> dict:
    """Expected wellbeing gain per scene (noise-free), optionally including personal taste."""
    gains = {}
    for key, (mood_change, stress_red) in expected_effects(ctx).items():
        if astronaut is not None:
            mood_change += astronaut.personal[key][0]
            stress_red += astronaut.personal[key][1]
        gains[key] = (
            _apply_headroom(mood_change, ctx["mood"])
            + 0.5 * _apply_stress_headroom(stress_red, ctx["stress"])
        )
    return gains


def sample_context(astronaut: Astronaut, day: int, drift: dict, rng: np.random.Generator) -> dict:
    phase = mission_phase(day)
    time_block = rng.choice(TIME_BLOCK_KEYS, p=TIME_BLOCK_WEIGHTS)
    phase_shift = {
        "adaptation": dict(mood=-0.1, energy=-0.35, stress=0.45, home=0.0, sleep=-0.6),
        "routine": dict(mood=0.0, energy=0.0, stress=0.0, home=0.0, sleep=0.0),
        "late": dict(mood=-0.35, energy=-0.2, stress=0.15, home=0.85, sleep=-0.2),
    }[phase]
    time_shift = {"morning": 0.3, "work": 0.0, "evening": -0.3, "pre_sleep": -0.8}[str(time_block)]

    # Slow day-to-day drift (AR(1)) shared across indicators gives realistic streaks.
    for name in drift:
        drift[name] = 0.75 * drift[name] + rng.normal(0, 0.35)
    sleep = astronaut.base_sleep + phase_shift["sleep"] + 0.8 * drift["sleep"] + rng.normal(0, 0.5)
    sleep = round(_clip(sleep, 3.0, 9.5) * 2) / 2
    sleep_effect = (sleep - 7) * 0.25

    def scale(value):
        return int(_clip(round(value), 1, 5))

    return {
        "mission_day": day,
        "mission_phase": phase,
        "time_block": str(time_block),
        "sleep_hours": sleep,
        "mood": scale(astronaut.base_mood + phase_shift["mood"] + drift["mood"] + sleep_effect + rng.normal(0, 0.5)),
        "energy": scale(astronaut.base_energy + phase_shift["energy"] + time_shift + drift["energy"] + sleep_effect * 1.5 + rng.normal(0, 0.5)),
        "stress": scale(astronaut.base_stress + phase_shift["stress"] + drift["stress"] - sleep_effect + rng.normal(0, 0.5)),
        "homesickness": scale(astronaut.base_home + phase_shift["home"] + drift["home"] + rng.normal(0, 0.5)),
    }


def sample_outcome(ctx: dict, scene: str, astronaut: Astronaut, rng: np.random.Generator) -> dict:
    """Simulate the re-check after running `scene` for this context."""
    mood_change, stress_red = expected_effects(ctx)[scene]
    mood_change += astronaut.personal[scene][0]
    stress_red += astronaut.personal[scene][1]
    mood_latent = _apply_headroom(mood_change, ctx["mood"]) + rng.normal(0, MOOD_NOISE_SD)
    stress_latent = _apply_stress_headroom(stress_red, ctx["stress"]) + rng.normal(0, STRESS_NOISE_SD)
    mood_after = int(_clip(round(ctx["mood"] + mood_latent), 1, 5))
    stress_after = int(_clip(round(ctx["stress"] - stress_latent), 1, 5))
    energy_shift = {"active": 0.4, "learning": 0.1, "family": 0.1, "nature": 0.0, "calm": -0.3}[scene]
    energy_after = int(_clip(round(ctx["energy"] + energy_shift + 0.3 * mood_latent + rng.normal(0, 0.4)), 1, 5))
    enjoyment = int(_clip(round(3 + 1.2 * mood_latent + 1.5 * astronaut.personal[scene][0] + rng.normal(0, 0.6)), 1, 5))
    planned = int(rng.choice(DURATION_CHOICES))
    # Sessions that feel bad are more often stopped early.
    completed = bool(rng.random() > _clip(0.08 - 0.15 * mood_latent, 0.02, 0.6))
    minutes = planned if completed else round(planned * rng.uniform(0.2, 0.8), 1)
    return {
        "planned_minutes": planned,
        "minutes_completed": minutes,
        "completed": completed,
        "mood_after": mood_after,
        "energy_after": energy_after,
        "stress_after": stress_after,
        "enjoyment": enjoyment,
        "gain": wellbeing_gain(ctx["mood"], mood_after, ctx["stress"], stress_after),
    }


def generate(astronauts: int = 60, mission_days: int = 180, checkins_per_week: float = 3.5, seed: int = 7) -> pd.DataFrame:
    """Generate the synthetic training set with a uniformly random logging policy."""
    rng = np.random.default_rng(seed)
    rows = []
    probability = checkins_per_week / 7
    for index in range(1, astronauts + 1):
        astronaut = make_astronaut(index, rng)
        drift = {"mood": 0.0, "energy": 0.0, "stress": 0.0, "home": 0.0, "sleep": 0.0}
        for day in range(1, mission_days + 1):
            context = sample_context(astronaut, day, drift, rng)
            if rng.random() > probability:
                continue
            scene = str(rng.choice(SCENE_KEYS))
            outcome = sample_outcome(context, scene, astronaut, rng)
            oracle = expected_gains(context, astronaut)
            rows.append({
                "astronaut_id": astronaut.astronaut_id,
                **context,
                "scene": scene,
                "propensity": 1 / len(SCENE_KEYS),
                **outcome,
                **{f"oracle_{key}": round(value, 4) for key, value in oracle.items()},
            })
    return pd.DataFrame(rows)

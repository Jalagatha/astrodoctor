"""Explicit demonstration placeholders. No validated clinical rules are supplied."""
INDICATORS = {
    "resting_hr": {"label": "Resting heart rate", "unit": "bpm", "domain": "Cardiovascular", "direction": 1, "floor": 1.5, "range": (25, 220)},
    "sleep_hours": {"label": "Sleep duration", "unit": "hours", "domain": "Sleep", "direction": -1, "floor": .3, "range": (0, 24)},
    "fatigue_score": {"label": "Fatigue", "unit": "score_1_5", "domain": "Fatigue and mood", "direction": 1, "floor": .5, "range": (1, 5)},
    "mood_score": {"label": "Mood", "unit": "score_1_5", "domain": "Fatigue and mood", "direction": -1, "floor": .5, "range": (1, 5)},
    "workload_score": {"label": "Workload", "unit": "score_1_5", "domain": "Workload", "direction": 1, "floor": .5, "range": (1, 5)},
    "sleep_quality": {"label": "Sleep quality", "unit": "score_1_5", "domain": "Sleep", "direction": -1, "floor": .5, "range": (1, 5)},
}
DOMAINS = {"Cardiovascular": ["resting_hr"], "Sleep": ["sleep_hours"], "Fatigue and mood": ["fatigue_score", "mood_score"], "Workload": ["workload_score"]}
DEFAULTS = {"linking_window_days": 3, "persistence_cycles_for_attention": 3, "min_baseline_samples": 7,
            "min_quality_score": .6, "stale_data_limit_days": 2, "baseline_window_days": 30,
            "robust_z_threshold": 3, "sustained_days": 2}
LEVEL_ORDER = {"URGENT": 0, "ATTENTION": 1, "OBSERVE": 2, "UNKNOWN": 3, "NORMAL": 4}
GLYPHS = {"NORMAL": "○", "OBSERVE": "◇", "ATTENTION": "▲", "URGENT": "⯃", "UNKNOWN": "⬚"}
# Links are hypotheses without reviewed references. Routine control events have no link rules.
LINK_RULES = {"solar_particle_event": {"sleep_hours", "resting_hr"}, "sleep_schedule_change": {"sleep_hours"}}

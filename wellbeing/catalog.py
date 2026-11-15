"""Fixed vocabulary for the wellbeing workflow: scenes, mission phases and time blocks.

Everything the recommender, the synthetic generator and the UI agree on lives here so
the three cannot drift apart. Adding a scene means adding it here, regenerating the
synthetic data and retraining (the model has one input column per scene).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Scene:
    key: str
    theme: str
    title: str
    summary: str
    arousal: str  # "low", "medium" or "high": how stimulating the scene is
    gradient: str  # CSS gradient used by the placeholder session player


SCENES = (
    Scene("family", "Family", "School run",
          "Walk the familiar route to school with your family on a bright morning.",
          "medium", "linear-gradient(135deg, #f6c177, #e98a6b 55%, #7c4d8a)"),
    Scene("nature", "Nature", "Forest rain",
          "Shelter under a forest canopy while soft rain falls around you.",
          "low", "linear-gradient(135deg, #2f6b4f, #1f4a3a 50%, #12302a)"),
    Scene("learning", "Learning", "Language lab",
          "A guided, playful lesson in a language you have chosen to learn.",
          "medium", "linear-gradient(135deg, #4a6fd1, #3a4fa0 55%, #2a2f6b)"),
    Scene("active", "Active play", "Football & bike",
          "Kick a ball around a sunny park, then ride a coastal bike path.",
          "high", "linear-gradient(135deg, #f2a541, #e0603f 55%, #9b2f3a)"),
    Scene("calm", "NASA calm", "Garden at dusk",
          "Sit in a quiet garden as the light fades and the first stars appear.",
          "low", "linear-gradient(135deg, #6c5b9e, #3b3f72 55%, #1b2240)"),
)
SCENE_KEYS = tuple(scene.key for scene in SCENES)
SCENES_BY_KEY = {scene.key: scene for scene in SCENES}

# Mission phase is derived from the mission day. The thresholds are prototype
# assumptions (first month = adaptation; after four months = long-duration fatigue).
MISSION_PHASES = (
    ("adaptation", "Early adaptation (days 1–30)"),
    ("routine", "Mid-mission (days 31–120)"),
    ("late", "Late mission (day 121+)"),
)
PHASE_KEYS = tuple(key for key, _ in MISSION_PHASES)


def mission_phase(mission_day: int) -> str:
    if mission_day <= 30:
        return "adaptation"
    if mission_day <= 120:
        return "routine"
    return "late"


# Time block within the crew day (ISS runs on UTC).
TIME_BLOCKS = (
    ("morning", "Morning, before work"),
    ("work", "Break during the work day"),
    ("evening", "Evening, off duty"),
    ("pre_sleep", "Wind-down before sleep"),
)
TIME_BLOCK_KEYS = tuple(key for key, _ in TIME_BLOCKS)


def default_time_block(hour_utc: int) -> str:
    if 5 <= hour_utc < 9:
        return "morning"
    if 9 <= hour_utc < 18:
        return "work"
    if 18 <= hour_utc < 21:
        return "evening"
    return "pre_sleep"


# Self-report scales (all 1–5). Labels are shown in the check-in and re-check forms.
SCALES = {
    "mood": ("Mood", ("Very low", "Low", "Okay", "Good", "Great")),
    "energy": ("Energy", ("Exhausted", "Tired", "Steady", "Lively", "Full of energy")),
    "stress": ("Stress", ("None", "Mild", "Moderate", "High", "Overwhelming")),
    "homesickness": ("Missing home", ("Not at all", "A little", "Somewhat", "A lot", "Intensely")),
    "enjoyment": ("Enjoyment of the session", ("Disliked it", "Not much", "Neutral", "Liked it", "Loved it")),
}

DURATION_CHOICES = (10, 15, 20, 25, 30)

# Safety rules applied before ranking. Each maps a scene to a predicate on the
# check-in context and the reason shown to the astronaut when it applies.
ELIGIBILITY_RULES = (
    ("active", lambda ctx: ctx["time_block"] == "pre_sleep",
     "High-arousal play is not offered in the wind-down before sleep."),
    ("learning", lambda ctx: ctx["sleep_hours"] < 4.5,
     "Learning is paused after very short sleep (under 4.5 h)."),
)


def blocked_reason(scene_key: str, context: dict):
    for key, predicate, reason in ELIGIBILITY_RULES:
        if key == scene_key and predicate(context):
            return reason
    return None


def wellbeing_gain(mood_before, mood_after, stress_before, stress_after) -> float:
    """The outcome the recommender learns to maximise.

    Mood change counts fully; stress reduction counts half. Both scales are 1–5,
    so the gain ranges from -6 to +6.
    """
    return (mood_after - mood_before) + 0.5 * (stress_before - stress_after)

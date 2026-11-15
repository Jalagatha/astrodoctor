"""Display-only helpers for the wellbeing pages (no effect on recommendations)."""
from .catalog import SCENES_BY_KEY, default_time_block
from .models import VRSession


def display_name(user) -> str:
    profile = getattr(user, "personal_profile", None)
    try:
        name = profile.display_name if profile else ""
    except AttributeError:
        name = ""
    return (name or user.get_short_name() or user.get_username()).split()[0]


def greeting(now) -> str:
    return {"morning": "Good morning", "work": "Good afternoon", "evening": "Good evening",
            "pre_sleep": "Rest well"}[default_time_block(now.hour)]


def home_stats(completed: list) -> dict:
    """`completed` = re-checked sessions, newest first."""
    lifts = [session.mood_after - session.checkin.mood for session in completed]
    days = sorted({session.checkin.mission_day for session in completed}, reverse=True)
    streak = 0
    for index, day in enumerate(days):
        if index and days[index - 1] - day > 1:
            break
        streak += 1
    by_scene = {}
    for session in completed:
        by_scene.setdefault(session.scene, []).append(session.gain)
    favourite = max(by_scene, key=lambda key: sum(by_scene[key]) / len(by_scene[key])) if by_scene else None
    return {
        "sessions": len(completed),
        "mean_lift": sum(lifts) / len(lifts) if lifts else None,
        "improved_share": round(100 * sum(lift > 0 for lift in lifts) / len(lifts)) if lifts else None,
        "streak": streak,
        "favourite": SCENES_BY_KEY.get(favourite),
    }


def mood_chart(completed: list, width=640, height=200, limit=12) -> dict | None:
    """Before/after mood polylines for the latest sessions (oldest on the left)."""
    sessions = list(reversed(completed[:limit]))
    if len(sessions) < 2:
        return None
    pad_x, pad_top, pad_bottom = 28, 16, 26
    step = (width - 2 * pad_x) / (len(sessions) - 1)

    def y(value):
        return pad_top + (5 - value) / 4 * (height - pad_top - pad_bottom)

    points = []
    for index, session in enumerate(sessions):
        x = pad_x + index * step
        points.append({"x": round(x, 1), "before": round(y(session.checkin.mood), 1), "after": round(y(session.mood_after), 1),
                       "day": session.checkin.mission_day, "scene": SCENES_BY_KEY[session.scene].theme,
                       "mood_before": session.checkin.mood, "mood_after": session.mood_after})
    return {
        "width": width, "height": height, "points": points,
        "before_line": " ".join(f"{p['x']},{p['before']}" for p in points),
        "after_line": " ".join(f"{p['x']},{p['after']}" for p in points),
        "after_area": f"{points[0]['x']},{height - pad_bottom} " + " ".join(f"{p['x']},{p['after']}" for p in points)
                      + f" {points[-1]['x']},{height - pad_bottom}",
        "grid": [{"value": value, "y": round(y(value), 1)} for value in range(1, 6)],
        "baseline": height - pad_bottom,
    }


def reason_items(reasons: list) -> list:
    items = []
    for text in reasons:
        if text.startswith("Exploring"):
            kind = "explore"
        elif "personal adjustment" in text:
            kind = "personal"
        elif " lowers " in text:
            kind = "down"
        else:
            kind = "up"
        items.append({"kind": kind, "text": text})
    return items


def gauge(value: float, full_scale: float = 2.0) -> int:
    """Percent for a ring gauge; `full_scale` maps to a full ring."""
    return int(max(3, min(100, round(100 * value / full_scale))))


def outcome_deltas(session: VRSession) -> list:
    checkin = session.checkin
    rows = [("Mood", checkin.mood, session.mood_after, True), ("Stress", checkin.stress, session.stress_after, False),
            ("Energy", checkin.energy, session.energy_after, None)]
    result = []
    for label, before, after, higher_is_better in rows:
        delta = after - before
        if higher_is_better is None or delta == 0:
            tone = "neutral"
        else:
            tone = "good" if (delta > 0) == higher_is_better else "bad"
        result.append({"label": label, "before": before, "after": after, "delta": delta, "tone": tone})
    return result

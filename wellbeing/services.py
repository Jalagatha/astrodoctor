import pandas as pd
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .catalog import SCENES
from .models import VRSession, WellbeingCheckIn
from .recommender import load_bundle, predict_gains, recommend


def model_bundle():
    return load_bundle(settings.WELLBEING_MODEL_PATH)


def personal_history(user):
    """(scene, residual) pairs from this astronaut's completed re-checks."""
    sessions = (VRSession.objects.filter(user=user, status=VRSession.RECHECKED, predicted_gain__isnull=False)
                .select_related("checkin"))
    return [(session.scene, session.residual) for session in sessions]


@transaction.atomic
def create_recommendation(checkin: WellbeingCheckIn, rng=None) -> VRSession:
    bundle = model_bundle()
    result = recommend(bundle, checkin.context(), personal_history(checkin.user), rng=rng)
    return VRSession.objects.create(
        checkin=checkin, user=checkin.user, model_version=result.model_version,
        recommended_scene=result.recommended, recommended_minutes=result.duration,
        exploring=result.exploring, ranking=[item.as_dict() for item in result.ranked],
        reasons=result.reasons,
    )


def start_session(session: VRSession, scene: str, minutes: int) -> VRSession:
    predictions = predict_gains(model_bundle(), session.checkin.context())
    session.scene = scene
    session.predicted_gain = predictions[scene]
    session.planned_minutes = minutes
    session.started_at = timezone.now()
    session.status = VRSession.STARTED
    session.save()
    return session


def end_session(session: VRSession) -> VRSession:
    now = timezone.now()
    elapsed = (now - session.started_at).total_seconds() / 60
    session.ended_at = now
    session.minutes_completed = round(min(elapsed, session.planned_minutes), 1)
    session.status = VRSession.ENDED
    session.save()
    return session


def theme_summary(user):
    """Per-scene personal stats for the home page."""
    sessions = list(VRSession.objects.filter(user=user, status=VRSession.RECHECKED).select_related("checkin"))
    summary = []
    for scene in SCENES:
        mine = [session for session in sessions if session.scene == scene.key]
        gains = [session.gain for session in mine]
        mood_changes = [session.mood_after - session.checkin.mood for session in mine]
        summary.append({
            "scene": scene, "sessions": len(mine),
            "mean_gain": sum(gains) / len(gains) if gains else None,
            "mean_mood_change": sum(mood_changes) / len(mood_changes) if mood_changes else None,
        })
    return summary


def sessions_frame() -> pd.DataFrame:
    """Completed real sessions in the training-data schema (for retraining)."""
    rows = []
    for session in VRSession.objects.filter(status=VRSession.RECHECKED).select_related("checkin"):
        checkin = session.checkin
        rows.append({
            "astronaut_id": f"USER-{session.user_id}", **checkin.context(), "mission_day": checkin.mission_day,
            "scene": session.scene, "gain": session.gain,
            "planned_minutes": session.planned_minutes, "minutes_completed": session.minutes_completed,
            "mood_after": session.mood_after, "energy_after": session.energy_after,
            "stress_after": session.stress_after, "enjoyment": session.enjoyment,
        })
    return pd.DataFrame(rows)

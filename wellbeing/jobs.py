"""Dataset generation and model training, shared by the Model page and the management commands.

The page starts a job and returns at once. The job runs in a background thread
(training takes about 30 s, longer than a typical web-server request timeout). The
TrainingJob row records progress so the page can show status and results. Only one
job runs at a time. A job left "running" by a server restart is marked failed
after STALE_AFTER.
"""
import os
import threading
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.db import close_old_connections, connection
from django.utils import timezone

from .models import TrainingJob
from .simulator import generate
from .training import save, train, validate_training_frame

STALE_AFTER = timedelta(minutes=20)
GENERATE_LIMITS = {"astronauts": (5, 500), "days": (30, 1000), "per_week": (0.5, 14.0)}
_start_lock = threading.Lock()


class JobBusy(RuntimeError):
    pass


# ---- Work functions (also used by the management commands) ----

def generate_dataset(output: Path, astronauts=60, days=180, per_week=3.5, seed=7) -> dict:
    frame = generate(astronauts, days, per_week, seed)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    frame.to_csv(temporary, index=False)
    os.replace(temporary, output)
    return {"rows": len(frame), "astronauts": int(frame["astronaut_id"].nunique()), "path": str(output)}


def train_and_save(data_path: Path, include_sessions=False, model_path: Path | None = None) -> dict:
    from .services import sessions_frame

    data = pd.read_csv(data_path)
    extra = sessions_frame() if include_sessions else None
    bundle, card = train(data, extra)
    save(bundle, card, model_path or settings.WELLBEING_MODEL_PATH)
    return card


def read_training_csv(upload) -> pd.DataFrame:
    """Parse and validate an uploaded CSV; raises ValueError with a readable message."""
    if not upload.name.lower().endswith(".csv"):
        raise ValueError("Upload a .csv file.")
    try:
        frame = pd.read_csv(upload)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise ValueError(f"Could not read the CSV: {exc}") from exc
    validate_training_frame(frame)
    return frame


def save_upload(frame: pd.DataFrame) -> Path:
    folder = Path(settings.WELLBEING_UPLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"training-{timezone.now():%Y%m%d-%H%M%S}.csv"
    frame.to_csv(path, index=False)
    return path


def dataset_info(path=None):
    path = Path(path or settings.WELLBEING_DATASET_PATH)
    if not path.exists():
        return None
    return _dataset_info(str(path), path.stat().st_mtime)


@lru_cache(maxsize=4)
def _dataset_info(path: str, mtime: float) -> dict:
    frame = pd.read_csv(path, usecols=["astronaut_id", "mission_day"])
    return {
        "rows": len(frame), "astronauts": int(frame["astronaut_id"].nunique()),
        "days": int(frame["mission_day"].max()), "path": path,
        "modified": datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone()),
        "size_kb": round(Path(path).stat().st_size / 1024),
    }


# ---- Job orchestration ----

def active_job():
    job = TrainingJob.objects.filter(status__in=[TrainingJob.QUEUED, TrainingJob.RUNNING]).first()
    if job and timezone.now() - (job.started_at or job.created_at) > STALE_AFTER:
        job.status, job.finished_at = TrainingJob.FAILED, timezone.now()
        job.error = "Interrupted: the job did not finish (was the server restarted?)."
        job.save(update_fields=["status", "finished_at", "error"])
        return None
    return job


def start_job(kind: str, params: dict, user=None) -> TrainingJob:
    with _start_lock:
        if active_job():
            raise JobBusy("Another dataset or training job is still running. Wait for it to finish.")
        job = TrainingJob.objects.create(kind=kind, params=params, created_by=user)
    if settings.WELLBEING_JOBS_SYNC:
        run_job(job.pk)
        job.refresh_from_db()
    else:
        threading.Thread(target=run_job, args=(job.pk,), daemon=True, name=f"wellbeing-job-{job.pk}").start()
    return job


def run_job(job_id: int) -> None:
    close_old_connections()
    try:
        job = TrainingJob.objects.get(pk=job_id)
        job.status, job.started_at = TrainingJob.RUNNING, timezone.now()
        job.save(update_fields=["status", "started_at"])
        try:
            if job.kind == TrainingJob.GENERATE:
                result = generate_dataset(settings.WELLBEING_DATASET_PATH, **job.params)
            else:
                card = train_and_save(Path(job.params["data_path"]), job.params.get("include_sessions", False))
                result = {key: card[key] for key in ("version", "data", "prediction", "policy",
                                                     "personalisation_simulation") if key in card}
        except Exception as exc:  # report any failure on the page rather than losing it in a thread
            job.status, job.error = TrainingJob.FAILED, f"{type(exc).__name__}: {exc}"
        else:
            job.status, job.result = TrainingJob.SUCCEEDED, result
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "result", "error", "finished_at"])
    finally:
        if not settings.WELLBEING_JOBS_SYNC:
            connection.close()  # this thread's own connection

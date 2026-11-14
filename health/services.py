import math
from uuid import UUID

import pandas as pd
from django.db import transaction

from engine import ALPHA, HARD_LIMITS, INDICATORS, Z_CUTS, analyse, simulate
from .models import CheckIn, DailyRecord, DatasetCalibration, DatasetLock

REQUIRED_COLUMNS = {"day", *INDICATORS}
OPTIONAL_COLUMNS = {"radiation_msv"}
SYMPTOMS = {
    "Headache",
    "Cough",
    "Rash",
    "Back pain",
    "Blurred vision",
    "Dizziness on standing",
    "Palpitations",
}
RECORD_COLUMNS = ("day", *INDICATORS, "radiation_msv")


def records_frame():
    rows = DailyRecord.objects.order_by("day").values(*RECORD_COLUMNS)
    return pd.DataFrame.from_records(rows, columns=RECORD_COLUMNS)


def save_frame(frame):
    rows = frame.astype(object).where(pd.notna(frame), None).to_dict("records")
    DailyRecord.objects.bulk_create([DailyRecord(**row) for row in rows], batch_size=500)


def parse_dataset(upload):
    if upload.size > 20 * 1024 * 1024:
        raise ValueError("The file must be 20 MB or smaller.")
    name = upload.name.lower()
    if name.endswith(".csv"):
        frame = pd.read_csv(upload)
    elif name.endswith(".xlsx"):
        frame = pd.read_excel(upload, engine="openpyxl")
    else:
        raise ValueError("Choose a .csv or .xlsx file.")

    frame.columns = [str(column).strip().lower() for column in frame.columns]
    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError("The file contains duplicate column names.")
    frame = frame.dropna(how="all").copy()
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}.")

    for column in REQUIRED_COLUMNS | (OPTIONAL_COLUMNS & set(frame.columns)):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[column].isna().any():
            raise ValueError(f"Column '{column}' contains blank or non-numeric values.")
        if not frame[column].map(math.isfinite).all():
            raise ValueError(f"Column '{column}' contains a non-finite value.")

    if (frame["day"] < 1).any() or not (frame["day"] % 1 == 0).all():
        raise ValueError("Mission day values must be positive whole numbers.")
    if frame["day"].duplicated().any():
        raise ValueError("Each mission day must appear only once.")
    if len(frame) < 21:
        raise ValueError("Upload at least 21 daily rows to calculate a personal baseline.")

    if "radiation_msv" not in frame:
        frame["radiation_msv"] = None
    frame["day"] = frame["day"].astype(int)
    return frame.loc[:, RECORD_COLUMNS].sort_values("day").reset_index(drop=True)


def import_dataset(frame, mode):
    if mode not in {"replace", "append"}:
        raise ValueError("Choose whether to replace or append the existing dataset.")

    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        if mode == "replace":
            CheckIn.objects.all().delete()
            DailyRecord.objects.all().delete()
        else:
            existing = set(
                DailyRecord.objects.filter(day__in=frame["day"].tolist())
                .values_list("day", flat=True)
            )
            conflicts = sorted(existing & set(frame["day"].tolist()))
            if conflicts:
                preview = ", ".join(map(str, conflicts[:8]))
                raise ValueError(f"Mission days already exist ({preview}); replace the dataset or remove those rows.")
        save_frame(frame)
        DatasetCalibration.objects.all().delete()


def load_demo_dataset():
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        if DailyRecord.objects.exists():
            return False
        save_frame(simulate())
        return True


def save_checkin(client_id, mood, stress, sleep_h, symptoms):
    try:
        client_uuid = UUID(str(client_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid check-in identifier.") from exc

    try:
        mood = int(mood)
        stress = int(stress)
        sleep_h = float(sleep_h)
    except (TypeError, ValueError) as exc:
        raise ValueError("Mood, stress, and sleep must be valid numbers.") from exc
    if not 1 <= mood <= 10 or not 1 <= stress <= 10:
        raise ValueError("Mood and stress must be between 1 and 10.")
    if not math.isfinite(sleep_h) or not 0 <= sleep_h <= 10:
        raise ValueError("Sleep must be between 0 and 10 hours.")
    if not isinstance(symptoms, list) or not all(isinstance(item, str) for item in symptoms):
        raise ValueError("Symptoms must be a list of symptom names.")
    if set(symptoms) - SYMPTOMS:
        raise ValueError("The check-in contains an unsupported symptom.")

    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        latest = DailyRecord.objects.order_by("-day").first()
        if latest is None:
            raise ValueError("Upload a dataset or load demo data before saving a check-in.")
        existing = CheckIn.objects.filter(client_id=client_uuid).first()
        if existing:
            return existing, False

        values = {
            field: getattr(latest, field)
            for field in RECORD_COLUMNS
            if field != "day"
        }
        values.update(day=latest.day + 1, mood=mood, stress=stress, sleep_h=sleep_h)
        record = DailyRecord.objects.create(**values)
        checkin = CheckIn.objects.create(
            client_id=client_uuid,
            day=record.day,
            mood=mood,
            stress=stress,
            sleep_h=sleep_h,
            symptoms=symptoms,
        )
        return checkin, True



def analyse_dataset(frame, upto=None):
    trained = DatasetCalibration.objects.filter(pk=1).first()
    calibration = {"means": trained.means, "deviations": trained.deviations} if trained else None
    return analyse(frame, upto=upto, calibration=calibration)


def train_dataset(baseline_rows):
    try:
        baseline_rows = int(baseline_rows)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Choose a whole number of baseline rows.") from exc
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        frame = records_frame()
        if baseline_rows < 21 or baseline_rows > len(frame) - 7:
            raise ValueError("Use at least 21 baseline rows and leave at least 7 later rows for evaluation.")
        values = frame[list(INDICATORS)]
        if not values.map(math.isfinite).all().all():
            raise ValueError("All indicator values must be finite numbers before training.")
        base = values.iloc[:baseline_rows]
        means, raw_sd = base.mean(), base.std()
        deviations = raw_sd.clip(lower=1e-6)
        calibration = {"means": means.to_dict(), "deviations": deviations.to_dict()}
        result = analyse(frame, calibration=calibration)
        holdout = frame.iloc[baseline_rows:]
        z = result["z"].iloc[baseline_rows:]
        flagged = (z[list(INDICATORS)] >= Z_CUTS[0]).any(axis=1)
        hard_flags = pd.Series(False, index=holdout.index)
        for key, test, _ in HARD_LIMITS:
            hard_flags |= holdout[key].map(test)
        per_indicator = [
            {"key": key, "label": meta[2], "unit": meta[3], "mean": float(means[key]),
             "deviation": float(deviations[key]), "flagged": int((z[key] >= Z_CUTS[0]).sum())}
            for key, meta in INDICATORS.items()
        ]
        warnings = [f"{INDICATORS[key][2]} has almost no variation in the baseline; drift scores may be very sensitive."
                    for key in INDICATORS if raw_sd[key] < 1e-6]
        baseline_hard_flags = pd.Series(False, index=base.index)
        for key, test, _ in HARD_LIMITS:
            baseline_hard_flags |= base[key].map(test)
        if baseline_hard_flags.any():
            warnings.append(f"{int(baseline_hard_flags.sum())} baseline rows cross fixed hard limits. Review whether this period represents a normal baseline.")
        if len(holdout) < 21:
            warnings.append("The evaluation segment is short; review results on more mission days.")
        report = {"total_rows": len(frame), "evaluation_rows": len(holdout),
                  "flagged_rows": int(flagged.sum()), "hard_limit_rows": int(hard_flags.sum()),
                  "first_day": int(frame.iloc[0].day), "baseline_end_day": int(frame.iloc[baseline_rows - 1].day),
                  "evaluation_start_day": int(holdout.iloc[0].day), "last_day": int(frame.iloc[-1].day),
                  "indicators": per_indicator, "warnings": warnings, "alpha": ALPHA}
        trained, _ = DatasetCalibration.objects.update_or_create(pk=1, defaults={
            "baseline_rows": baseline_rows, "means": calibration["means"],
            "deviations": calibration["deviations"], "report": report,
        })
        return trained

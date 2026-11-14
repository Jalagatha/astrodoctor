import hashlib
import json
import math
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from openpyxl import load_workbook

from health.models import DatasetLock
from .audit import record
from .models import Astronaut, DemoAccount, Exposure, ImportReport, Observation, RuleVersion
from .rules import DEFAULTS, INDICATORS, LINK_RULES

SCHEMAS = {
    "astronauts": {"astronaut_id", "display_name", "mission_role", "baseline_start_day", "status", "origin_label"},
    "users": {"user_id", "display_name", "role", "astronaut_id", "origin_label"},
    "observations_daily": {"observation_id", "astronaut_id", "mission_day", "indicator_code", "value", "unit", "source_type", "quality_flag", "origin_label", "scenario_tag"},
    "exposures": {"exposure_id", "scope", "exposure_type", "start_day", "end_day", "magnitude", "unit", "source", "origin_label", "notes"},
    "scenario_parameters": {"parameter", "value", "status", "note"},
}


def positive_int(value):
    number = float(value)
    if not math.isfinite(number) or number < 1 or number % 1 or number > 1000000:
        raise ValueError("Mission days must be positive whole numbers no greater than 1000000.")
    return int(number)


def quality(code, value, flag):
    low, high = INDICATORS[code]["range"]
    if flag != "ok":
        return False, 0.0, f"Quality flag: {flag}. Confirm or correct this observation."
    if not low <= value <= high:
        return False, 0.0, "Outside the placeholder plausibility range. Confirm or correct this observation."
    return True, 1.0, ""


def import_workbook(file, actor="import"):
    raw = file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise ValueError("Workbook must be 20 MB or smaller.")
    from io import BytesIO
    workbook = load_workbook(BytesIO(raw), read_only=True, data_only=True)
    tables = {}
    try:
        for name, required in SCHEMAS.items():
            if name not in workbook.sheetnames:
                raise ValueError(f"Missing worksheet: {name}.")
            rows = workbook[name].iter_rows(values_only=True)
            headers = [str(value or "").strip() for value in next(rows)]
            if len(headers) != len(set(headers)) or required - set(headers):
                raise ValueError(f"Invalid {name} columns. Required: {', '.join(sorted(required))}.")
            tables[name] = [(number, dict(zip(headers, row))) for number, row in enumerate(rows, 2) if any(value is not None for value in row)]
    finally:
        workbook.close()
    report = {"counts": {}, "rejected": [], "excluded_observations": 0, "parameters": {}, "warnings": []}
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        for sheet in SCHEMAS:
            counts = {"source": len(tables[sheet]), "loaded": 0, "unchanged": 0, "rejected": 0}
            report["counts"][sheet] = counts
            for row_number, row in tables[sheet]:
                try:
                    with transaction.atomic():
                        if sheet == "scenario_parameters":
                            name = row["parameter"]
                            if name not in DEFAULTS or row["status"] != "placeholder":
                                raise ValueError("Unknown parameter or missing placeholder status.")
                            value = float(row["value"])
                            if not math.isfinite(value) or value <= 0 or (name == "min_quality_score" and value > 1):
                                raise ValueError("Invalid parameter value.")
                            if name != "min_quality_score" and (value % 1 or value > 365):
                                raise ValueError("Day and cycle parameters must be whole numbers up to 365.")
                            if name in report["parameters"]:
                                raise ValueError("Duplicate parameter.")
                            report["parameters"][name] = value
                            counts["loaded"] += 1
                            continue
                        if row["origin_label"] != "SYNTHETIC":
                            raise ValueError("Only explicitly SYNTHETIC demonstration records are accepted.")
                        if sheet == "astronauts":
                            model, identifier = Astronaut, row["astronaut_id"]
                            data = {key: row[key] for key in ("display_name", "mission_role", "status", "origin_label")}
                            data["baseline_start_day"] = positive_int(row["baseline_start_day"])
                        elif sheet == "users":
                            model, identifier = DemoAccount, row["user_id"]
                            role = {"admin": "rule_administrator", "rule_admin": "rule_administrator"}.get(row["role"], row["role"])
                            if role not in {"astronaut", "medical_officer", "flight_surgeon", "scientist", "rule_administrator"}:
                                raise ValueError("Unsupported account role.")
                            astronaut = row["astronaut_id"] or None
                            if (role == "astronaut") != bool(astronaut):
                                raise ValueError("Astronaut accounts require exactly one astronaut scope.")
                            if astronaut and not Astronaut.objects.filter(pk=astronaut).exists():
                                raise ValueError("Unknown astronaut.")
                            data = {"display_name": row["display_name"], "role": role, "astronaut_id": astronaut}
                        elif sheet == "observations_daily":
                            model, identifier = Observation, row["observation_id"]
                            code, value = row["indicator_code"], float(row["value"])
                            if code not in INDICATORS or row["unit"] != INDICATORS[code]["unit"] or not math.isfinite(value):
                                raise ValueError("Unknown indicator, incorrect unit, or non-finite value.")
                            if not Astronaut.objects.filter(pk=row["astronaut_id"]).exists():
                                raise ValueError("Unknown astronaut.")
                            accepted, score, reason = quality(code, value, row["quality_flag"])
                            data = {key: row[key] or "" for key in ("astronaut_id", "indicator_code", "unit", "source_type", "quality_flag", "origin_label", "scenario_tag")}
                            data.update(mission_day=positive_int(row["mission_day"]), value=value, accepted=accepted, quality_score=score, exclusion_reason=reason)
                            if Observation.objects.filter(astronaut_id=data["astronaut_id"], mission_day=data["mission_day"], indicator_code=code).exclude(pk=identifier).exists():
                                raise ValueError("A different observation already exists for this astronaut, day, and indicator.")
                        else:
                            model, identifier = Exposure, row["exposure_id"]
                            if row["scope"] != "crew" and not Astronaut.objects.filter(pk=row["scope"]).exists():
                                raise ValueError("Unknown exposure scope.")
                            data = {key: str(row[key] or "") for key in ("scope", "exposure_type", "magnitude", "unit", "source", "origin_label", "notes")}
                            data.update(start_day=positive_int(row["start_day"]), end_day=positive_int(row["end_day"]))
                            if data["end_day"] < data["start_day"]:
                                raise ValueError("Exposure ends before it starts.")
                        if not identifier or not str(identifier).strip():
                            raise ValueError("Missing record identifier.")
                        existing = model.objects.filter(pk=identifier).first()
                        if existing:
                            if any(getattr(existing, key) != value for key, value in data.items()):
                                raise ValueError("Identifier already exists with different content; original record preserved.")
                            counts["unchanged"] += 1
                        else:
                            instance = model(pk=identifier, **data)
                            instance.full_clean()
                            instance.save()
                            counts["loaded"] += 1
                        if sheet == "observations_daily" and not accepted:
                            report["excluded_observations"] += 1
                except (ValueError, TypeError, OverflowError, ValidationError, IntegrityError) as exc:
                    # Each rejected source row is reported; the remaining rows continue.
                    counts["rejected"] += 1
                    report["rejected"].append({"sheet": sheet, "row": row_number, "reason": str(exc)})
        params = {**DEFAULTS, **report["parameters"]}
        content = {"parameters": params, "indicators": INDICATORS, "links": {key: sorted(value) for key, value in LINK_RULES.items()}, "engine": "median-mad-v1"}
        rule_hash = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
        rule, _ = RuleVersion.objects.get_or_create(pk=f"demo-{rule_hash[:16]}", defaults={"parameters": params, "content_hash": rule_hash})
        report["rule_version"] = rule.pk
        report["warnings"].append("All thresholds and link rules are demonstration placeholders. No reviewed urgent protocol was supplied; urgent detection is not enabled.")
        result = ImportReport.objects.create(filename=Path(getattr(file, "name", "workbook.xlsx")).name, content_hash=hashlib.sha256(raw).hexdigest(), report=report)
        record(actor, "workbook_import", payload={"report_id": result.pk, "sha256": result.content_hash, "counts": report["counts"]})
    return result

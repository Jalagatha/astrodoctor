"""Chronological, quality-first demonstration engine; all thresholds are placeholders."""
from collections import defaultdict
from statistics import median

from django.db import transaction
from django.db.models import Q
from health.models import DatasetLock
from .audit import record
from .models import Assessment, Astronaut, Exposure, Finding, Observation, RuleVersion
from .rules import DOMAINS, GLYPHS, INDICATORS, LINK_RULES


def assess_astronaut(astronaut, rule):
    parameters = rule.parameters
    observations = list(Observation.objects.filter(astronaut=astronaut).order_by("mission_day", "id"))
    if not observations:
        return 0
    indexed = defaultdict(dict)
    for obs in observations:
        indexed[obs.mission_day][obs.indicator_code] = obs
    exposures = list(Exposure.objects.filter(Q(scope="crew") | Q(scope=astronaut.pk)))
    history, streaks, observe_cycles = defaultdict(list), defaultdict(int), defaultdict(int)
    last_accepted = {}
    created_count = 0
    for day in range(astronaut.baseline_start_day, max(indexed) + 1):
        metrics = {}
        for code, meta in INDICATORS.items():
            if code == "sleep_quality":
                continue
            current = indexed[day].get(code)
            previous = [(d, v) for d, v in history[code] if d >= day - parameters["baseline_window_days"]]
            values = [v for _, v in previous]
            center = median(values) if values else None
            mad = median([abs(value - center) for value in values]) if values else None
            spread = max((mad or 0) * 1.4826, meta["floor"])
            approved = bool(current and current.accepted and current.quality_score >= parameters["min_quality_score"])
            provisional = len(values) < parameters["min_baseline_samples"]
            z = meta["direction"] * (current.value - center) / spread if approved and center is not None else None
            changed = bool(z is not None and z >= parameters["robust_z_threshold"] and not provisional)
            streaks[code] = streaks[code] + 1 if changed else 0
            last = last_accepted.get(code)
            metrics[code] = {
                "code": code, "label": meta["label"], "unit": meta["unit"],
                "value": current.value if current else None,
                "observation_id": current.pk if current else None,
                "accepted": approved, "reason": current.exclusion_reason if current else "No measurement received for this mission day.",
                "median": center, "mad": mad, "spread": spread, "sample_count": len(values), "provisional": provisional,
                "baseline_days": [d for d, _ in previous], "data_age": day - last[0] if last else None,
                "last_value": last[1] if last else None,
                "z": round(z, 3) if z is not None else None, "streak": streaks[code],
                "onset_day": day - streaks[code] + 1 if changed else None,
            }
            if approved:
                metrics[code]["data_age"] = 0
        domains = []
        for domain, codes in DOMAINS.items():
            measures = [metrics[code] for code in codes]
            unavailable = any(not metric["accepted"] for metric in measures)
            provisional = any(metric["provisional"] for metric in measures)
            sustained = [metric for metric in measures if metric["streak"] >= parameters["sustained_days"]]
            confidence = "low" if unavailable or provisional else "medium"
            if unavailable or provisional:
                level = "UNKNOWN"
                observe_cycles[domain] = 0
            elif sustained:
                observe_cycles[domain] += 1
                level = "ATTENTION" if observe_cycles[domain] >= parameters["persistence_cycles_for_attention"] else "OBSERVE"
            else:
                level = "NORMAL"
                observe_cycles[domain] = 0
            links = []
            for metric in sustained:
                for exposure in exposures:
                    if metric["code"] not in LINK_RULES.get(exposure.exposure_type, set()):
                        continue
                    onset = metric["onset_day"]
                    if exposure.start_day <= onset <= exposure.end_day + parameters["linking_window_days"] and exposure.start_day <= day:
                        links.append({"exposure_id": exposure.pk, "type": exposure.exposure_type, "indicator": metric["code"], "start_day": exposure.start_day,
                                      "onset_day": onset, "evidence_tag": "hypothesized", "source": exposure.source,
                                      "reference": None, "association": "Temporal association only; causation is not established."})
            reasons = [f"{metric['label']}: {metric['sample_count']} prior quality-approved baseline samples." for metric in measures]
            if unavailable:
                reasons.append("Missing or excluded current measurements; last values are not treated as new observations.")
            if provisional:
                reasons.append("Baseline is provisional: the minimum sample count has not been reached.")
            if links:
                reasons.append("Exposure links are hypotheses without a reviewed scientific reference.")
            reasons.append("Synthetic input and placeholder rules; confidence is not a clinical probability.")
            details = {
                "domain": domain, "level": level, "glyph": GLYPHS[level], "metrics": measures, "confidence": confidence,
                "confidence_reasons": reasons, "links": links, "observe_cycles": observe_cycles[domain],
                "what_changed": "; ".join(f"{metric['label']} is outside its directional baseline band for {metric['streak']} consecutive days" for metric in sustained) or ("Current data or a sufficient baseline is unavailable." if level == "UNKNOWN" else "No sustained directional deviation detected."),
                "why_it_matters": "Repeated changes may warrant a review of measurements and mission context. This is a prototype association, not an established cause.",
                "limits": "Only supplied indicators are assessed. Missing values are not imputed. Rules and minimum effects are demonstration placeholders; no validated urgent protocol has been supplied.",
                "next_step": "Repeat and confirm the measurements; review the exposure timeline with the medical officer." if sustained else "Confirm flagged measurements or supply missing observations." if unavailable else "Continue recording observations.",
                "rule_version": rule.pk, "origin_label": "SYNTHETIC",
            }
            domains.append(details)
            if level in {"OBSERVE", "ATTENTION", "URGENT"}:
                finding, created = Finding.objects.get_or_create(astronaut=astronaut, mission_day=day, domain=domain, rule=rule, defaults={"level": level, "details": details})
                if created:
                    record("engine", "finding_created", astronaut.pk, {"finding_id": finding.pk, "day": day, "level": level, "rule": rule.pk})
                    created_count += 1
        domains.append({"domain": "Environment", "level": "NORMAL" if any(event.start_day <= day for event in exposures) else "UNKNOWN",
                        "glyph": "○" if any(event.start_day <= day for event in exposures) else "⬚", "metrics": [], "confidence": "low", "links": [],
                        "what_changed": "Exposure context only. No quantitative environmental risk or radiation dose is inferred from placeholder magnitudes."})
        _, created = Assessment.objects.get_or_create(astronaut=astronaut, mission_day=day, rule=rule, defaults={"domains": domains})
        if created:
            record("engine", "assessment_created", astronaut.pk, {"day": day, "rule": rule.pk, "levels": {d["domain"]: d["level"] for d in domains}})
        # Today's values enter history only after today's assessment (no future leakage).
        for code, obs in indexed[day].items():
            if obs.accepted and obs.quality_score >= parameters["min_quality_score"]:
                history[code].append((day, obs.value))
                last_accepted[code] = (day, obs.value)
    return created_count


def replay(rule=None):
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        rule = rule or RuleVersion.objects.order_by("-created_at").first()
        if not rule:
            raise ValueError("Import a Meridian workbook before running assessments.")
        count = sum(assess_astronaut(astronaut, rule) for astronaut in Astronaut.objects.all())
        return count

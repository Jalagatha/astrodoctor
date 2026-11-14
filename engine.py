"""Astro-Doctor core engine: simulation, personal baselines, drift detection,
readiness score, alerts with explanations, and recommended actions."""
import numpy as np
import pandas as pd

# indicator -> (domain, bad_direction (+1 = rising is bad), label, unit)
INDICATORS = {
    "resting_hr":  ("Cardiovascular", +1, "Resting heart rate", "bpm"),
    "hrv_rmssd":   ("Cardiovascular", -1, "Heart rate variability", "ms"),
    "spo2":        ("Cardiovascular", -1, "Blood oxygen (SpO2)", "%"),
    "grip_kg":     ("Musculoskeletal", -1, "Grip strength", "kg"),
    "resist_min":  ("Musculoskeletal", -1, "Resistive exercise", "min/day"),
    "body_temp":   ("Immune", +1, "Body temperature", "C"),
    "sleep_h":     ("Sleep", -1, "Sleep duration", "h"),
    "mood":        ("Behavioral", -1, "Mood (1-10)", "score"),
    "stress":      ("Behavioral", +1, "Stress (1-10)", "score"),
}
DOMAIN_WEIGHTS = {"Cardiovascular": .25, "Musculoskeletal": .2, "Immune": .15,
                  "Sleep": .15, "Behavioral": .25}
HARD_LIMITS = [  # (indicator, test, message) -> immediate RED regardless of baseline
    ("spo2", lambda v: v < 92, "SpO2 below 92%"),
    ("body_temp", lambda v: v >= 38.0, "Fever of 38.0 C or above"),
    ("resting_hr", lambda v: v > 100, "Resting heart rate above 100 bpm"),
    ("mood", lambda v: v <= 2, "Very low mood - please contact the CMO"),
]
RADIATION_LIMIT_MSV = 600.0   # illustrative mission dose budget
BASELINE_DAYS, ALPHA = 21, 0.3
LEVELS = ["Green", "Yellow", "Orange", "Red"]
Z_CUTS = (3.0, 6.0, 12.0)      # EWMA z-score cut-offs for Yellow/Orange/Red

ACTIONS = {
    "Cardiovascular": {
        "Yellow": ["Do the orthostatic self-test (lie 5 min, stand, record HR/BP).", "Check hydration and cabin CO2 log."],
        "Orange": ["Repeat BP and ECG patch reading twice today.", "Reduce high-intensity exercise 48 h; notify the CMO."],
        "Red": ["Stop exertion, sit down, take ECG/SpO2 now.", "Contact the CMO and ground flight surgeon immediately."]},
    "Musculoskeletal": {
        "Yellow": ["Complete today's full resistive (ARED) session.", "Log any back or joint pain."],
        "Orange": ["Review prescribed vs actual loading with the CMO.", "Add a second resistive session this week and recheck grip strength."],
        "Red": ["Report to the CMO: possible injury or severe deconditioning."]},
    "Immune": {
        "Yellow": ["Re-take temperature in 4 h and log symptoms (cough, rash, wounds)."],
        "Orange": ["Isolate from crew where possible; run the infection symptom checklist.", "Notify the CMO."],
        "Red": ["Contact the CMO now; start the infection protocol."]},
    "Sleep": {
        "Yellow": ["Keep a fixed sleep window; dim lights 1 h before bed."],
        "Orange": ["Use scheduled light therapy; avoid caffeine after midday; tell the CMO."],
        "Red": ["Request a workload and schedule review; CMO consult."]},
    "Behavioral": {
        "Yellow": ["Schedule a call with family or friends.", "Take 20 min of non-work time today."],
        "Orange": ["Talk to the CMO or ground psychologist this week.", "Do the cognitive test to check for fatigue effects."],
        "Red": ["Talk to the CMO or ground psychologist today. You are not alone."]},
    "Radiation": {
        "Yellow": ["Review dose budget with ground; use the shielded area for rest and sleep."],
        "Orange": ["Limit time outside the shielded area; ground to reassess the plan."],
        "Red": ["Move to the storm shelter and follow the radiation protocol."]},
}

def simulate(days=180, seed=7):
    """Synthetic mission with injected deterioration events (for demo/validation)."""
    r = np.random.default_rng(seed); d = np.arange(1, days + 1)
    ramp = lambda start, span: np.clip((d - start) / span, 0, 1)
    df = pd.DataFrame({"day": d})
    df["resting_hr"] = 58 + r.normal(0, 1.5, days) + 14 * ramp(90, 60)
    df["hrv_rmssd"] = 62 + r.normal(0, 4, days) - 28 * ramp(90, 60)
    df["spo2"] = 97.5 + r.normal(0, .5, days) - 2.5 * ramp(140, 30)
    df["resist_min"] = np.clip(45 + r.normal(0, 6, days) - 30 * ramp(60, 20) * (d < 120), 0, None)
    df["grip_kg"] = 46 + r.normal(0, .8, days) - 6 * ramp(70, 80)
    df["body_temp"] = 36.7 + r.normal(0, .12, days) + 1.3 * ((d >= 150) & (d <= 155))
    df["sleep_h"] = 7.2 + r.normal(0, .4, days) - 2.2 * ramp(115, 50)
    df["mood"] = np.clip(7.5 + r.normal(0, .6, days) - 4.2 * ramp(120, 55), 1, 10)
    df["stress"] = np.clip(3 + r.normal(0, .6, days) + 4 * ramp(120, 55), 1, 10)
    df["radiation_msv"] = np.cumsum(1.8 + r.normal(0, .15, days) + 40 * (d == 100))
    return df

def analyse(df, upto=None, calibration=None):
    """Return per-day z-scores, current status per domain, alerts, readiness."""
    df = df if upto is None else df[df.day <= upto]
    if df.empty:
        raise ValueError("At least one daily record is required for analysis.")
    base = df.iloc[:BASELINE_DAYS]
    if calibration is None:
        mu, sd = base[list(INDICATORS)].mean(), base[list(INDICATORS)].std().clip(lower=1e-6)
    else:
        mu = pd.Series(calibration["means"], dtype=float).reindex(INDICATORS)
        sd = pd.Series(calibration["deviations"], dtype=float).reindex(INDICATORS)
        if not np.isfinite(mu).all() or not np.isfinite(sd).all() or (sd <= 0).any():
            raise ValueError("The trained baseline contains invalid statistics.")
    ew_sd = np.sqrt(ALPHA / (2 - ALPHA))
    z = pd.DataFrame({"day": df.day})
    for k, (_, sign, _, _) in INDICATORS.items():
        ew = df[k].ewm(alpha=ALPHA, adjust=False).mean()
        z[k] = sign * (ew - mu[k]) / (sd[k] * ew_sd)   # positive = drifting the bad way
    last = df.iloc[-1]; zl = z.iloc[-1]
    alerts, dom_level, dom_score = [], {}, {}
    for dom in DOMAIN_WEIGHTS:
        ks = [k for k, v in INDICATORS.items() if v[0] == dom]
        worst = max(zl[k] for k in ks)
        lvl = sum(worst >= c for c in Z_CUTS)
        for k, test, msg in HARD_LIMITS:
            if k in ks and test(last[k]):
                lvl = 3; alerts.append(dict(domain=dom, level="Red", why=msg, indicator=k))
        for k in ks:
            if zl[k] >= Z_CUTS[0]:
                lab, unit = INDICATORS[k][2], INDICATORS[k][3]
                now = df[k].tail(7).mean(); chg = 100 * (now - mu[k]) / mu[k] if mu[k] != 0 else 0
                l = sum(zl[k] >= c for c in Z_CUTS)
                alerts.append(dict(domain=dom, level=LEVELS[l], indicator=k,
                    why=f"{lab}: 7-day average {now:.1f} {unit} vs personal baseline {mu[k]:.1f} ({chg:+.0f}%), drift z={zl[k]:.1f}"))
        dom_level[dom] = LEVELS[lvl]
        dom_score[dom] = float(100 - 75 * min(max(worst, 0) / Z_CUTS[2], 1))
    dose = last.get("radiation_msv")
    if pd.isna(dose):
        pct, projected, rl = None, None, 0
    else:
        pct = 100 * dose / RADIATION_LIMIT_MSV
        rl = 3 if pct >= 100 else 2 if pct >= 85 else 1 if pct >= 70 else 0
        projected = dose / last.day * 180
        if rl:
            alerts.append(dict(domain="Radiation", level=LEVELS[rl], indicator="radiation_msv",
                why=f"Cumulative dose {dose:.0f} mSv = {pct:.0f}% of the {RADIATION_LIMIT_MSV:.0f} mSv budget"))
    dom_level["Radiation"] = LEVELS[rl]
    readiness = sum(DOMAIN_WEIGHTS[d] * dom_score[d] for d in DOMAIN_WEIGHTS)
    top = max(LEVELS.index(v) for v in dom_level.values())
    readiness = min(readiness, [100, 85, 65, 40][top])   # a critical domain caps the score
    for a in alerts:
        a["actions"] = ACTIONS[a["domain"]].get(a["level"], [])
    alerts.sort(key=lambda a: -LEVELS.index(a["level"]))
    return dict(z=z, levels=dom_level, scores=dom_score, alerts=alerts, readiness=readiness,
                baseline=mu, radiation_pct=pct, radiation_projected=projected)

if __name__ == "__main__":
    df = simulate()
    for day in (30, 80, 110, 135, 152, 180):
        r = analyse(df, day)
        print(day, round(r["readiness"]), r["levels"])

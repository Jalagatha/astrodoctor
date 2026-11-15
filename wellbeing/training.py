"""Train and evaluate the population scene-recommendation model.

Pipeline:
1. Split astronauts 80/20 (whole people held out, so the test checks generalisation to
   a new crew member, not to unseen days of known people).
2. Fit a gradient-boosted regressor on (context, scene) → measured wellbeing gain.
3. Evaluate prediction error, the quality of the scene it would pick, and, using the
   simulator's oracle, how the personal bandit layer improves over repeated sessions.
4. Refit on all data and save the model bundle and a JSON model card.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

from .catalog import PHASE_KEYS, SCENE_KEYS, TIME_BLOCK_KEYS, blocked_reason
from .features import FEATURE_COLUMNS, encode
from .recommender import personal_adjustments, rank_scenes

REQUIRED_COLUMNS = ("astronaut_id", "mood", "energy", "stress", "homesickness", "sleep_hours",
                    "mission_phase", "time_block", "scene", "gain")


MIN_ROWS = 200
MIN_ASTRONAUTS = 5


def validate_training_frame(data: pd.DataFrame) -> None:
    """Raise ValueError with a readable message if `data` cannot be trained on."""
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Training data is missing columns: {', '.join(missing)}")
    empty = [column for column in REQUIRED_COLUMNS if data[column].isna().any()]
    if empty:
        raise ValueError(f"Training data has empty values in: {', '.join(empty)}")
    allowed = {"scene": SCENE_KEYS, "mission_phase": PHASE_KEYS, "time_block": TIME_BLOCK_KEYS}
    for column, values in allowed.items():
        unknown = sorted(set(data[column].astype(str)) - set(values))
        if unknown:
            raise ValueError(f"Unknown {column} values: {', '.join(unknown[:5])}. Allowed: {', '.join(values)}")
    for column in ("mood", "energy", "stress", "homesickness", "sleep_hours", "gain"):
        if not pd.api.types.is_numeric_dtype(data[column]):
            raise ValueError(f"Column {column} must be numeric.")
    for column in ("mood", "energy", "stress", "homesickness"):
        if not data[column].between(1, 5).all():
            raise ValueError(f"Column {column} must be on the 1–5 scale.")
    if not data["sleep_hours"].between(0, 14).all():
        raise ValueError("Column sleep_hours must be between 0 and 14.")
    if len(data) < MIN_ROWS or data["astronaut_id"].nunique() < MIN_ASTRONAUTS:
        raise ValueError(f"Need at least {MIN_ROWS} rows from {MIN_ASTRONAUTS} astronauts; got {len(data)} rows "
                         f"from {data['astronaut_id'].nunique()}.")


def build_model() -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        learning_rate=0.05, max_iter=500, max_leaf_nodes=15, min_samples_leaf=30,
        l2_regularization=1.0, early_stopping=True, validation_fraction=0.15,
        n_iter_no_change=25, random_state=0,
    )


def predict_matrix(model, frame: pd.DataFrame) -> np.ndarray:
    """Predicted gain for every (row, scene): shape (rows, scenes)."""
    columns = []
    for key in SCENE_KEYS:
        columns.append(model.predict(encode(frame, [key] * len(frame))))
    return np.column_stack(columns)


def eligibility_mask(frame: pd.DataFrame) -> np.ndarray:
    records = frame.loc[:, ["time_block", "sleep_hours"]].to_dict("records")
    return np.array([[blocked_reason(key, ctx) is None for key in SCENE_KEYS] for ctx in records])


def _best(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return np.where(mask, values, -np.inf).argmax(axis=1)


def evaluate_policies(model, test: pd.DataFrame) -> dict:
    """Static (no personal history) policy quality on held-out astronauts."""
    oracle = test.loc[:, [f"oracle_{key}" for key in SCENE_KEYS]].to_numpy()
    mask = eligibility_mask(test)
    predicted = predict_matrix(model, test)
    rows = np.arange(len(test))
    model_pick = _best(predicted, mask)
    oracle_pick = _best(oracle, mask)
    random_value = float(np.mean([oracle[i][mask[i]].mean() for i in rows]))
    fixed = {key: float(np.where(mask[:, j], oracle[:, j], np.nan).mean()) for j, key in enumerate(SCENE_KEYS)}
    best_fixed_key = max(fixed, key=fixed.get)
    model_value = float(oracle[rows, model_pick].mean())
    oracle_value = float(oracle[rows, oracle_pick].mean())

    # Inverse-propensity estimate of the model policy from the logged (random) outcomes:
    # what we could report even without an oracle.
    logged = test["scene"].map(SCENE_KEYS.index).to_numpy()
    matched = (model_pick == logged)
    ips = float(np.mean(matched / test["propensity"].to_numpy() * test["gain"].to_numpy()))
    return {
        "expected_gain_random": round(random_value, 3),
        "expected_gain_best_single_scene": round(fixed[best_fixed_key], 3),
        "best_single_scene": best_fixed_key,
        "expected_gain_model": round(model_value, 3),
        "expected_gain_oracle_population_plus_personal": round(oracle_value, 3),
        "share_of_achievable_uplift_over_random": round((model_value - random_value) / (oracle_value - random_value), 3),
        "top1_agreement_with_oracle": round(float((model_pick == oracle_pick).mean()), 3),
        "ips_estimated_gain_model_from_logged_outcomes": round(ips, 3),
        "logged_mean_gain_random_policy": round(float(test["gain"].mean()), 3),
        "pick_distribution": {key: round(float((model_pick == j).mean()), 3) for j, key in enumerate(SCENE_KEYS)},
    }


def simulate_personalisation(model, test: pd.DataFrame, residual_sd: float, noise_sd: float, seed: int = 11) -> dict:
    """Replay each held-out astronaut's check-ins in order. Compare the population-only
    policy with population + personal bandit, observing noisy outcomes drawn from the oracle."""
    rng = np.random.default_rng(seed)
    predicted_all = predict_matrix(model, test)
    oracle_all = test.loc[:, [f"oracle_{key}" for key in SCENE_KEYS]].to_numpy()
    mask_all = eligibility_mask(test)
    contexts = test.loc[:, ["time_block", "sleep_hours"]].to_dict("records")
    results = {"population_only": [], "population_plus_bandit": [], "oracle": []}
    late = {key: [] for key in results}
    for _, positions in test.reset_index(drop=True).groupby("astronaut_id", sort=True).indices.items():
        positions = sorted(positions, key=lambda i: test.iloc[i]["mission_day"])
        history = []
        for step, i in enumerate(positions):
            predictions = dict(zip(SCENE_KEYS, predicted_all[i]))
            personal = personal_adjustments(history, residual_sd)
            ranked = rank_scenes(predictions, personal, contexts[i], rng=rng, explore=True)
            bandit_key = ranked[0].key
            j_bandit = SCENE_KEYS.index(bandit_key)
            j_pop = int(_best(predicted_all[i:i + 1], mask_all[i:i + 1])[0])
            j_oracle = int(_best(oracle_all[i:i + 1], mask_all[i:i + 1])[0])
            observed = oracle_all[i, j_bandit] + rng.normal(0, noise_sd)
            history.append((bandit_key, observed - predicted_all[i, j_bandit]))
            for name, j in (("population_only", j_pop), ("population_plus_bandit", j_bandit), ("oracle", j_oracle)):
                results[name].append(oracle_all[i, j])
                if step >= len(positions) // 2:
                    late[name].append(oracle_all[i, j])
    return {
        "astronauts": int(test["astronaut_id"].nunique()),
        "sessions": len(results["oracle"]),
        "mean_expected_gain_all_sessions": {k: round(float(np.mean(v)), 3) for k, v in results.items()},
        "mean_expected_gain_second_half": {k: round(float(np.mean(v)), 3) for k, v in late.items()},
    }


def train(data: pd.DataFrame, extra: pd.DataFrame | None = None, seed: int = 0) -> tuple:
    """Return (bundle, card). `extra` holds real recorded sessions (no oracle columns);
    it is added to training data but never to the synthetic evaluation."""
    validate_training_frame(data)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    train_idx, test_idx = next(splitter.split(data, groups=data["astronaut_id"]))
    train_rows, test_rows = data.iloc[train_idx], data.iloc[test_idx]

    model = build_model().fit(encode(train_rows, train_rows["scene"]), train_rows["gain"])
    test_X = encode(test_rows, test_rows["scene"])
    predicted = model.predict(test_X)
    scene_means = train_rows.groupby("scene")["gain"].mean()
    baseline = test_rows["scene"].map(scene_means).to_numpy()
    residual_sd = float(np.std(test_rows["gain"].to_numpy() - predicted))

    card = {
        "data": {
            "rows": len(data), "astronauts": int(data["astronaut_id"].nunique()),
            "train_rows": len(train_rows), "test_rows": len(test_rows),
            "test_astronauts": int(test_rows["astronaut_id"].nunique()),
            "real_session_rows_added": 0 if extra is None else len(extra),
            "gain_mean": round(float(data["gain"].mean()), 3), "gain_sd": round(float(data["gain"].std()), 3),
        },
        "prediction": {
            "rmse_model": round(float(np.sqrt(mean_squared_error(test_rows["gain"], predicted))), 3),
            "rmse_scene_mean_baseline": round(float(np.sqrt(mean_squared_error(test_rows["gain"], baseline))), 3),
            "mae_model": round(float(mean_absolute_error(test_rows["gain"], predicted)), 3),
            "r2_model": round(float(r2_score(test_rows["gain"], predicted)), 3),
            "r2_scene_mean_baseline": round(float(r2_score(test_rows["gain"], baseline)), 3),
        },
    }
    if all(f"oracle_{key}" in data.columns for key in SCENE_KEYS):
        oracle_logged = test_rows.apply(lambda row: row[f"oracle_{row['scene']}"], axis=1).to_numpy()
        noise_sd = float(np.std(test_rows["gain"].to_numpy() - oracle_logged))
        card["policy"] = evaluate_policies(model, test_rows)
        card["personalisation_simulation"] = simulate_personalisation(model, test_rows, residual_sd, noise_sd)

    # Final model: all synthetic rows plus any recorded sessions.
    full = data if extra is None or extra.empty else pd.concat([data, extra], ignore_index=True)
    final = build_model().fit(encode(full, full["scene"]), full["gain"])
    version = "scene-rec-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    card.update({
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "algorithm": "HistGradientBoostingRegressor (scikit-learn) on context + one-hot scene; "
                     "personal layer: Normal–Normal Thompson sampling on residuals",
        "sklearn_version": sklearn.__version__,
        "features": list(FEATURE_COLUMNS),
        "target": "wellbeing gain = (mood after − mood before) + 0.5 × (stress before − stress after)",
        "residual_sd": round(residual_sd, 3),
        "boosting_iterations": int(final.n_iter_),
    })
    bundle = {"model": final, "scenes": list(SCENE_KEYS), "features": list(FEATURE_COLUMNS),
              "version": version, "residual_sd": residual_sd, "card": card}
    return bundle, card


def save(bundle: dict, card: dict, model_path: Path) -> Path:
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    # Write then rename so a running app never loads a half-written file.
    temporary = model_path.with_name(model_path.name + ".tmp")
    joblib.dump(bundle, temporary)
    os.replace(temporary, model_path)
    card_path = model_path.with_name("model_card.json")
    card_path.write_text(json.dumps(card, indent=2))
    return card_path

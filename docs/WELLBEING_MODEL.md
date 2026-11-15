# Wellbeing workflow, dataset and scene recommender

> Prototype. The dataset is synthetic and its effect sizes are design assumptions, not spaceflight or clinical evidence. Nothing here is validated for crew use.

## Workflow

| Step | What happens | Code |
| --- | --- | --- |
| **Check-in** | Mood, energy, stress and missing home (each 1–5), hours slept, mission day and time of day. Mission phase is derived from the mission day. | `WellbeingCheckIn`, `/wellbeing/check-in/` |
| **Adaptive engine** | The population model predicts each scene's wellbeing gain for this check-in. The personal layer adjusts it from the astronaut's past re-checks. Safety rules remove unsuitable scenes, and the engine suggests a session length. | `wellbeing/recommender.py` |
| **VR session** | The astronaut can accept the suggestion or pick another scene, then chooses 10–30 minutes. The placeholder player counts down. The server records the minutes actually spent. | `VRSession`, `/wellbeing/session/<id>/` |
| **Re-check** | Mood, energy, stress and enjoyment after the session. The gain and its difference from the prediction (the residual) feed the next recommendation. | `/wellbeing/session/<id>/recheck/` |

## Theme worlds

| Key | Theme | Scene | Arousal |
| --- | --- | --- | --- |
| `family` | Family | School run | medium |
| `nature` | Nature | Forest rain | low |
| `learning` | Learning | Language lab | medium |
| `active` | Active play | Football & bike | high |
| `calm` | NASA calm | Garden at dusk | low |

The catalogue lives in `wellbeing/catalog.py`. To add a scene: add it there, regenerate the data, give it a response function in `simulator.expected_effects`, then retrain. The model has one input per scene, and a model trained on a different catalogue refuses to load.

## Outcome (training target)

```
wellbeing gain = (mood after − mood before) + 0.5 × (stress before − stress after)
```

Gain ranges from −6 to +6. Enjoyment, energy after the session and minutes completed are recorded but not part of the target. They are available for a different target later.

## Mission phase and time of day

| Phase | Mission days |
| --- | --- |
| `adaptation` | 1–30 |
| `routine` | 31–120 |
| `late` | 121+ |

Time of day is one of `morning`, `work` (a break during the work day), `evening` or `pre_sleep`. The form pre-selects one from the UTC hour.

## Synthetic dataset — `data/wellbeing_synthetic.csv`

Generate it with `python manage.py generate_wellbeing_data` (defaults: 60 astronauts, 180-day missions, about 3.5 check-ins per week, seed 7, giving about 5,400 rows). The output is deterministic for a given seed.

| Column | Meaning |
| --- | --- |
| `astronaut_id` | Synthetic person (`SYN-001` …) |
| `mission_day`, `mission_phase`, `time_block` | When the check-in happened |
| `mood`, `energy`, `stress`, `homesickness` | Check-in, 1–5 |
| `sleep_hours` | Previous night, 3–9.5 h in 0.5 h steps |
| `scene` | Scene that was run, assigned uniformly at random |
| `propensity` | Probability of that assignment (0.2), used for off-policy evaluation |
| `planned_minutes`, `minutes_completed`, `completed` | Session length. Sessions that feel bad are stopped early more often. |
| `mood_after`, `energy_after`, `stress_after`, `enjoyment` | Re-check, 1–5 |
| `gain` | Training target (formula above) |
| `oracle_<scene>` | Noise-free expected gain of each scene for this person and context. **Evaluation only, never a model input.** |

### How the data is generated

1. **People.** Each astronaut has baseline mood, energy, stress, homesickness and sleep. They also have a personal taste offset per scene (SD 0.35), which is what the personal layer has to discover.
2. **Days.** Day-to-day drift is an AR(1) process. Phase effects:
   - Adaptation: worse sleep, higher stress, lower energy.
   - Late mission: more homesickness, lower mood.
   - Time of day: energy falls through the day.
   - Short sleep: lowers mood and energy and raises stress.
3. **Scene response.** These are the assumptions; edit `expected_effects` to change them. Each scene changes mood and stress like this:
   - **Family:** helps most when missing home, especially in late mission. When someone is both very homesick and very low, it can backfire.
   - **Nature:** broadly helpful, and best for high stress and late mission (nature deprivation).
   - **Learning:** best when rested, energetic and calm, and during the day. Poor when tired, short of sleep or stressed.
   - **Active play:** lifts low mood if there is energy for it. It is harmful before sleep, during early adaptation, or when exhausted.
   - **NASA calm:** best for stress, tiredness, sleep debt and the wind-down before sleep. It is dull when lively.
4. **Ceiling effects.** Mood near 5 has little room to rise, and stress near 1 has little room to fall.
5. **Noise.** Mood noise has SD 0.55 and stress noise SD 0.5. The results are then rounded back onto the 1–5 scales, as real self-reports would be.

With personal taste included, the best scene for a given row is spread across all five themes, each winning in roughly 15–27% of rows.

## Model

**Population model.** `HistGradientBoostingRegressor` (scikit-learn), trained on the context features plus a one-hot encoding of the scene. To score a check-in, the model makes one prediction per scene. Feature encoding is shared by training and inference in `wellbeing/features.py`.

**Personal layer (contextual bandit).** For each scene, the engine keeps a Normal–Normal posterior over the astronaut's offset from the population prediction:
- The prior is N(0, 0.35²).
- The observations are their re-check residuals, with noise SD equal to the model's held-out residual SD.

Thompson sampling then draws one value from each posterior and adds it to the prediction. As a result:
- Scenes with little personal evidence still get tried occasionally.
- Scenes that consistently do better or worse for this person move up or down.

When the sampled choice differs from the best expected scene, the page says the engine is exploring.

**Safety rules** (`catalog.ELIGIBILITY_RULES`), applied before ranking:
- No Active play in the pre-sleep wind-down.
- No Learning after less than 4.5 h of sleep.

**Session length** (a rule, not learned). The default is 20 minutes, adjusted as follows:
- 10 minutes during a work break.
- 25 minutes for a low-arousal scene when stress is 4 or higher.
- At most 15 minutes when energy is 2 or lower, or before sleep.

**Explanations** are counterfactual. Each part of the check-in is reset to a typical value (mood 3, energy 3, stress 2, missing home 2, 7 h sleep, mid-mission, evening), and the change in the recommended scene's predicted gain is reported. Personal history and exploration each add a line.

## Evaluation

Run `python manage.py train_recommender`. Whole astronauts are held out (80/20 split by person), so the test measures performance for a crew member the model has never seen. Results are written to `ml_models/model_card.json` and shown at `/wellbeing/model/` (staff only).

Results from the committed dataset (seed 7):

| Metric | Value |
| --- | --- |
| RMSE, model vs. per-scene average | 0.76 vs 0.81 (R² 0.10 vs −0.01) |
| Expected gain: random scene / best single scene (calm) / model picks / oracle | 0.35 / 0.43 / 0.58 / 0.81 |
| Share of achievable uplift over random | 50% |
| Off-policy (IPS) estimate of the model policy from logged outcomes | 0.57 |
| Online replay, second half of each mission: population model only / + personal bandit / oracle | 0.61 / 0.74 / 0.87 |

Low R² is expected here. Individual outcomes are noisy integer changes, and what matters is ranking scenes correctly, which the policy metrics measure. In the online replay, the personal layer closes about half of the remaining gap to the oracle as re-checks accumulate.

## Managing the dataset and model from the UI

Staff can manage both from **Model** (`/wellbeing/model/`):

- **Generate dataset.** Set astronauts, mission length, check-ins per week and seed. This replaces `data/wellbeing_synthetic.csv`. **Download CSV** saves the current file.
- **Train model.** Train on the synthetic dataset or on an uploaded CSV, optionally adding the re-checks recorded in the app.
  - Uploads are checked before training: required columns, allowed values, 1–5 scales, and at least 200 rows from 5 astronauts. Uploads are kept in `data/uploads/`, which git ignores.
  - The new model replaces the old one in a single step, and the app uses it from the next recommendation.
- **Recent runs.** Shows each run's status, duration, scores or error.

Jobs run in a background thread inside the web server, one at a time, and the page refreshes itself until the job finishes. A job interrupted by a server restart is marked failed after 20 minutes. The management commands below do the same work from the terminal.

## Retraining with real sessions

`python manage.py train_recommender --include-sessions` adds every completed re-check in the database to the training data, while evaluation stays on synthetic data. Recorded sessions are not randomised: the engine chose them. Before relying on real data, either:
- keep a share of randomised sessions, or
- store the selection probability for each session and use off-policy corrections.

`VRSession.ranking` already stores the scores seen at decision time.

## Limitations and open decisions

- All effect sizes are assumptions. Replace or calibrate the simulator with pilot or analog-mission data before drawing any conclusions.
- The check-in uses four 1–5 scales plus sleep. Validated instruments, such as short forms of PANAS or POMS, may be more appropriate.
- Scenes are placeholders. The headset content and any personal Family media still need to be produced.
- Inference runs on the server, so check-ins need a connection; there is no offline queue.
- Mood data is visible only to its owner. Crew-level views and access for medical or psychological support staff have not been designed.

# Meridian implementation alignment

## Source and scope

Prepared from the user-supplied draft v1.0 documents:

- NASA_Space_Apps_Prototype_Description (1).pdf, especially sections 4, 6, 8–12.
- NASA_Space_Apps_System_Flow_Document (1).pdf, especially processes 2–15 and sections 5–12.
- Meridian_Synthetic_Dataset (1).xlsx, inspected separately.

The documents describe the target product. Their setup commands, suggested credentials, open tasks, and role assignments are reference material, not actions automatically authorized by opening a document. The official challenge statement and referenced Technical Requirements Document, Technical Blueprint, visual design direction, rule files, reviewed templates, and emergency protocols were not supplied or verified.

## Intended demonstration

Meridian is an offline-capable astronaut health decision-support prototype. Its principal story is a temporal association between a recorded solar event, reduced sleep, and rising resting heart rate. Findings must explain the measurements, evidence tags, confidence, limitations, rule version, and next step without claiming causation or clinical validation.

The synthetic workbook is the native demonstration input, not a malformed version of the current wide-format health import. Keep its indicators and units unchanged. Do not substitute fatigue for stress, workload for exercise duration, or invent absent measurements.

## Current implementation versus target

| Area | Current repository | Required behavior |
| --- | --- | --- |
| Health storage | One shared wide `DailyRecord` dataset | Observations keyed by astronaut, day, and indicator, with original identifier, units, source, quality, and origin |
| Personnel | Editable crew directory and independent account profiles | Explicit account role and astronaut scope linked to observation ownership |
| Imports | First worksheet, nine mandatory indicators | Named workbook sheets; astronauts, observations, exposures, scenario parameters; load report with rejected rows and reasons |
| Baselines | First-21 mean/sample SD, optional saved calibration | Per-astronaut, per-indicator median/MAD; approved samples only; sample count and provisional state; chronological assessment |
| Quality | Basic numeric validation | Preserve raw observations; assess quality before baseline and alert processing; extreme-value confirmation prompts |
| Alerts | Generated Green/Yellow/Orange/Red summaries | Stored NORMAL/OBSERVE/ATTENTION/URGENT/UNKNOWN assessments, confidence, persistence, and rule versions |
| Missing data | Complete-row import requirement; check-ins copy old measurements | Missing/stale domains UNKNOWN with data age; never create new wearable observations by copying yesterday's values |
| Exposures | Not represented | Individual and crew-scoped events on the same time axis; recorded temporal links with evidence and references |
| Finding detail | Inline alert explanation/actions | Fixed explanation order; acknowledge, dismiss with reason, escalate; persistent lifecycle |
| Access | Predominantly Django staff access | Astronaut own-only; medical officer crew access; flight surgeon limits; scientist aggregate-only; rule administrator limited access |
| Offline | Cached shell and check-in outbox | Last-loaded screens/data, findings and permitted actions accessible offline; pending count, sync time, priority and conflict handling |
| Audit | No clinical action history | Append-only actions with actor, reason, original values, rule version, chained hashes and verification |
| Interface | Top navigation, artwork, editable profiles/developers | Role-aware desktop sidebar and phone bottom navigation; persistent mode/status line; synthetic and placeholder labels |

The optional avatar/camera, artwork preferences, and developer directory can remain supporting features. They do not substitute for the main demonstration.

## Implementation sequence and completion criteria

1. **Store and workbook ingestion.** Add scoped astronaut/observation/exposure/parameter entities and an explicit import action. Validate sheet schemas, units, identifiers, scopes, and synthetic origin. Preserve original rows and provenance. Load 3 astronauts, 7 account definitions, 442 observations, 4 exposures, and 5 scenario parameters, or report every rejection. Account definitions must not grant privileges to arbitrary uploaded users or create guessed/shared passwords. Preserve the existing dataset during development; do not silently replace it.
2. **Quality and robust baselines.** Process observations in mission-day order with no future data leakage. Implement median/MAD, sample counts, provisional status, exclusion reasons, and data-age handling. Keep unknowns distinct from normal. Mark undefined quality and deviation settings as placeholders.
3. **Scoped overview and access checks.** Bind user roles and astronaut scopes explicitly. Check server-side access on every route before sending individual data. Present daily history and domain status, with 7/14/30-day filters and quality visibility controls.
4. **Exposure linking and assessment.** Store only links satisfying precedence, direction, effect size, and linking-window conditions. Keep evidence tags and source references. Do not claim that the synthetic solar event caused the changes. Version rules; record assessment inputs and confidence reasons.
5. **Findings and actions.** Implement the required reading order, stored alert states, acknowledge/dismiss/escalate, and audit records. Require dismissal reasons. Acknowledgement must not change assessed severity.
6. **Timeline and check-in.** Show exposure lanes, baseline bands and selected mission day. Keep self-report scales at 1–5. Separate received wearable measurements from user-confirmed corrections. Save actual observations, not cloned complete daily rows.
7. **Offline demonstration.** Scope local data to the signed-in account and clear/isolate it across account switches. Preserve permitted screens and actions offline; run the required local checks; expose an outbox with idempotency keys, pending count, last successful sync, and retry/conflict behavior. Test a complete disconnected scenario, not only an offline fallback page.
8. **Additional clinical/team workflows.** Build crew ranking, protocol-driven triage, non-URGENT overrides, audit verification, simulated ground summaries/guidance, and read-only rules view according to priority and available reviewed content.

Access controls and audit design begin with the schema; they must not be postponed until after individual data is exposed.

## Dataset acceptance scenarios

- **AST-01:** Establish the normal history through day 19. Show the day-20 solar event and days-20–22 sleep-schedule event. On day 22, explain the observed sleep/heart-rate changes with temporal association, evidence status and confidence. Persistence behavior must follow documented rules rather than hardcoding an expected outcome.
- **AST-02:** Wearable observations are absent on days 10–13. Sleep and resting-heart-rate domains show UNKNOWN and data age, even though self-reports still exist. Missing values do not become zeros or carried-forward measurements.
- **AST-03:** The flagged day-15 resting heart rate of 142 produces a quality-confirmation prompt and is excluded from baseline/alert processing pending the quality decision. It must not become an automatic health alert merely because the old engine has an HR hard limit.
- **Control exposures:** Routine mission/workload events produce no invented exposure links.
- **Scope:** AST-02 cannot obtain AST-01 records by editing a URL or API payload; failed access is audited. Scientist responses exclude individual identities and daily records.
- **Actions:** Dismissal without a reason fails; acknowledgement preserves severity; recurrence is not silently suppressed; unauthorized or URGENT overrides fail.
- **Offline:** Open the scenario, disconnect, review findings, perform an allowed action/check-in, verify queued writes, reconnect, and verify idempotent delivery and updated status.

## Decisions and inconsistencies to resolve

- **Technology stack:** The prototype description specifies React/TypeScript/Vite/Workbox/Dexie and FastAPI/SQLAlchemy/SQLite, with SQLCipher where configured. This repo uses Django templates, vanilla JavaScript, PostgreSQL, and Streamlit. Product requirements can guide an incremental implementation, but an exact blueprint implementation requires an explicit stack decision. No framework rewrite has been performed.
- **Baseline evolution:** Define rolling-window length and whether current/deviating samples enter the baseline before or after assessment. Avoid accidentally absorbing the demonstrated deviation or using later days to assess earlier days. The previous train/apply mean-SD feature is a legacy path, not the specified Meridian model.
- **Quality and rule values:** The workbook provides some placeholder parameters, but not all plausibility ranges, robust-deviation cutoffs, persistence definitions, confidence weights, effect sizes, templates, and urgent criteria. Do not present implementation choices as medically approved or tune rules solely to force the desired scenario.
- **Urgent override conflict:** Both documents repeatedly prohibit medical-officer overrides on URGENT alerts; the flow document's alert-transition section also mentions an URGENT downgrade by override. Use the repeated prohibition as the conservative working interpretation pending clarification.
- **Confidence precedence:** Low confidence caps ordinary findings at OBSERVE, while urgent checks are required immediately. Specify that confidence must not silently suppress an approved urgent rule; confirm the intended ordering with the requirements owner.
- **Exposure timestamp wording:** Process 5 describes rejecting future exposures unless marked backdated, which is internally inconsistent. Distinguish scheduled future events from historical corrections before implementing this validation.
- **P0/P1 boundary:** The prototype labels Crew View as P1 but includes it in the main acceptance script. Treat the minimal read-only crew list as necessary for the requested demonstration; keep advanced triage/overrides separate until their protocol inputs exist.
- **Offline meanings:** Distinguish loss of the external ground link while the local laptop service remains available from total browser-to-service disconnection. The documents require cached screens and local behavior; the current server-only assessment cannot fulfill browser-disconnected operation by itself.
- **Offline sign-in:** Demonstration account switching while disconnected needs a defined local demo identity design. Do not weaken production Django authentication to imitate demo selection.

## Status

This is an implementation alignment and acceptance plan. The Meridian ingestion, scoped engine, exposure linking, alert lifecycle, and full offline workflow have not yet been implemented. Existing tests cover the legacy dashboard and recently added features; they do not demonstrate compliance with the two supplied documents.

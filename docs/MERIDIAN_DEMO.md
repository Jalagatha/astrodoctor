# Run the Meridian demonstration

The original workbook is included at `demo_data/Meridian_Synthetic_Dataset.xlsx`. The mission screens use its native five indicators and preserve the 1–5 self-report scales. The older wide-format Astro-Doctor importer and training screen are separate legacy features; they are not used by Meridian assessments.

## Local setup

From the project directory, run:

```sh
.venv/bin/python manage.py migrate --settings=config.demo_settings
.venv/bin/python manage.py seed_meridian --settings=config.demo_settings --demo-accounts
.venv/bin/python manage.py load_triage_protocol demo_data/triage_workflow_demo.json --demonstration --settings=config.demo_settings
.venv/bin/python manage.py runserver --settings=config.demo_settings
```

This opt-in configuration uses `meridian-demo.sqlite3` in the project directory and HTTP localhost for a synthetic-only demonstration. The seed command prints a different random password for each newly created demo account. Save these locally. Existing usernames, passwords and role assignments are never overwritten. To change a demo password later:

```sh
.venv/bin/python manage.py changepassword U-AST-01 --settings=config.demo_settings
```

Open `http://127.0.0.1:8000/`, sign in, and the app routes to your role's mission view. Demo accounts are:

| Username | Role |
| --- | --- |
| U-AST-01 / U-AST-02 / U-AST-03 | Own astronaut only |
| U-MO-01 | Medical officer: crew, findings, actions, audit and rules |
| U-FS-01 | Flight surgeon: read-only crew/triage; delivered ground summaries and guidance authoring |
| U-SCI-01 | Pooled crew summary only |
| U-ADM-01 | Rule administrator: import, rules and audit |

For an existing Django deployment, migrate and run `seed_meridian` with its normal settings. Account creation is a separate development-only option; a superuser can instead assign explicit **Mission access** records in Django admin. A generic staff flag does not grant mission data access. Uploaded account definitions never create login credentials or elevate existing users.

## Walk through the supplied scenarios

1. Sign in as **U-AST-01**. Set mission day to **22** and apply. Cardiovascular and Sleep show **OBSERVE**, with trends, previous-sample median/MAD baselines, and hypothesized exposure associations. Open the findings lower on the page to read the explanation and act on them.
2. Dismissal requires a reason. Acknowledge and escalate preserve assessed severity. Each action creates a durable actor/reason audit entry. A retry uses the same identifier.
3. Sign in as **U-AST-02**, and select days **10–13**. Missing heart-rate and sleep observations show **UNKNOWN** and their data age. Manual self-reports remain available.
4. Sign in as **U-AST-03**, and select day **15**. The heart-rate value **142** appears in a quality prompt. It is excluded from baselines and does not produce a health alert. Toggle **Show excluded** to inspect it on the chart.
5. Sign in as **U-MO-01** to open each astronaut's overview, inspect findings, and verify the audit chain.
6. Sign in as **U-SCI-01**. Only pooled indicator summaries are returned; individual astronaut routes are refused.
7. Sign in as **U-ADM-01** to inspect the load report and read-only rule version. Reimporting the same workbook reports unchanged records. Conflicting identifiers are rejected with the original data retained.

Expected initial load: **3 astronauts, 7 account definitions, 442 observations, 4 exposures, 5 scenario parameters, and 1 excluded quality observation**. The initial replay creates 90 daily assessments. Rule thresholds are documented implementation placeholders, not clinical reference ranges.

## Medical-officer, triage, and ground workflow

1. Sign in as **U-MO-01**. In Mission home, select **day 22**, open AST-01, expand a finding, and choose **Finding history & triage**.
2. In **Medical-officer override**, choose a non-URGENT displayed level and enter a reason. The engine's assessed level stays intact; the overview, alerts, crew view for that mission day, and ground summary identify the override. History records each change. URGENT overrides are rejected server-side, including direct requests.
3. Select **Start triage**, then **Synthetic finding review checklist**. This is an explicitly unapproved, nonclinical demonstration of branching and record keeping. No clinical criteria or emergency steps were invented. Answer the first question; different options lead to different branches. Pause and resume from the **Triage** list. Answers are saved with their actor and time and cannot be silently rewritten by stale forms. Finish to queue a summary with the pinned protocol version/hash.
4. Open **Ground link** as U-MO-01. It starts offline. Enable **Simulated ground link available**, select **Update link**, then **Send pending summaries**. Packets are delivered to the local ground inbox in priority order; repeating delivery does not duplicate records. This is a server-side demonstration, with no external transmission.
5. Sign in as **U-FS-01**, open **Ground link**, then a delivered summary. Enter **Guidance to the onboard team** and save. Pending, undelivered packets are inaccessible to the flight-surgeon role. The simulated link must be available for new guidance.
6. Sign in as **U-AST-01** or U-MO-01, open **Guidance**, and mark the message as read. Read receipts are recorded separately for each actor. Other astronauts cannot view or acknowledge AST-01's messages. Guidance never changes observations or assessed severity.

The workflow test in `tests/workflows.browser.cjs` exercises this whole handoff using the synthetic accounts, including pause/resume and mobile rendering. It leaves demonstration sessions/messages and an audit history, and restores the tested finding's displayed level at the end.

### Supplied protocol versions

The `load_triage_protocol` command validates a JSON document with `id`, `title`, and `definition`. `definition.questions` contains questions with unique `code`, `prompt`, and `options`; each option has a unique `value`, a `label`, and `next` (another question code or null to finish). Cycles, unreachable questions, invalid branches, and duplicate options are rejected. Sessions pin a version and verify its content hash before each transition. Existing versions cannot be overwritten; supply a new ID for a revision.

For an externally reviewed protocol, omit `--demonstration` and supply `--approved-by` and `--approval-reference`. These record supplied approval metadata; the application does not certify medical validity. An option marked `urgent: true` requires `definition.emergency_steps`. A matched urgent branch immediately displays those supplied steps, records the time, and queues a priority-zero packet. The included demonstration checklist cannot contain urgent medical criteria. Without any loaded protocol, the triage start screen explains that a protocol is required.

These triage, override, guidance, and ground-link forms require connectivity to the local mission service. They work while the simulated external ground link is disabled, except delivery and new ground guidance. They are not yet queued in the browser when the local service itself is unavailable.

## Offline behavior implemented

Open an astronaut overview while connected first. The page stores its last-loaded snapshot in IndexedDB. **Simulate ground link offline** queues actions while the local Django service remains available. Browser disconnection also supports the last-loaded snapshot through the service-worker offline page, once the worker is installed and controlling the page. Revisit or reload while connected once after first install.

Findings can be read and actions/check-ins queued while disconnected. Pending count and last sync are visible. Reconnect and select **Sync**. Escalations are sent before routine actions and check-ins; retries keep their identifiers. The server checks the current account before sync. Conflicting or rejected items remain queued and are shown as errors rather than silently overwritten. Logging out removes the view snapshot; pending items stay isolated under their owner and can be sent when that owner next signs in.

New check-ins use a new mission day and explicitly entered measurements. Blank wearable fields stay missing. Their assessment runs after delivery to the local service. Historical measurement correction and local browser assessment are not implemented. Cached access is for the last-loaded synthetic demo session; offline account switching is unavailable.

## Scope and remaining document requirements

Implemented: native workbook import with rejection reporting; astronaut scope; chronological median/MAD baselines; provisional/missing-data status; quality exclusion; sustained drift and persistence; recorded exposure associations; confidence reasons; versioned rule outputs; interactive timeline; finding actions; check-ins; local snapshot/outbox; audit verification; role-specific data access; developer/profile/camera UI retained; non-URGENT overrides with history; versioned branching triage with pause/resume; priority ground outbox; scoped guidance and per-actor read receipts.

Not yet implemented: reviewed urgent rules and protocols; exposure-entry forms; confirmation/correction of flagged measurements; full offline account selection and browser-side assessment; conflict resolution UI; multi-device sync; database encryption. No URGENT alert is generated without an approved rule. The supplied documents omit reviewed medical rule files and contain conflicting urgent-override wording; those need an explicit specification before enabling them.

The app remains Django/vanilla JavaScript. React/FastAPI/SQLCipher from the proposed blueprint have not been adopted. A chained audit detects edits within retained entries but is not externally anchored and cannot prove that an entire tail was not removed. All demonstration findings identify synthetic data and placeholder rules.

## Checks

```sh
DJANGO_DEBUG=true DATABASE_URL=sqlite:///:memory: .venv/bin/python manage.py test
node --test tests/ui.test.cjs tests/camera.test.cjs
```


Browser smoke test: `tests/meridian.browser.cjs` uses Playwright with a running localhost demo and the local credential file from initial account creation. It opens AST-01 day 22, checks the OBSERVE screen, disconnects, reloads the cached view, queues an acknowledgement, reconnects, verifies delivery, and checks the mobile page for horizontal overflow. It performs a real acknowledgement in the synthetic demo database. Point `MERIDIAN_CHROME` at an installed Chrome executable when its default macOS path does not apply.

Current verification: 52 Django tests and 10 JavaScript tests pass. The desktop/mobile overview smoke test and the medical-officer → flight-surgeon → astronaut workflow test passed with no page errors, cached offline reading, and successful queued-action delivery. PostgreSQL concurrency, encryption, and physical-device camera testing were not performed in this local SQLite run.

# OrbitalForge Ultimate v3.0.0

OrbitalForge is an autonomous, quality-gated research-software factory for **AI/ML, robotics,
scientific data processing, remote sensing, and satellite systems**. Once this repository is on the
GitHub default branch and the `OPENAI_API_KEY` repository secret exists, GitHub Actions schedules one
bounded research cycle every ten minutes. The system resumes persistent state, advances the active
project, validates the candidate in an isolated temporary copy, independently reviews milestones, and
archives a project only after deterministic gates and a final scientific/software audit pass. It then
starts the next project automatically. After the seed program is exhausted, it designs a new
non-duplicate project that again integrates all four core domains.

OrbitalForge is built to produce **real software progress**, not empty activity. No-op candidates are
rejected, failed candidates are rolled back, and generated work is never allowed to edit the
orchestrator, workflows, state machinery, or repository control files directly.

## Upload-and-run setup

There is only one credential step that cannot safely be embedded in a ZIP:

1. Extract and commit **the complete archive**, including `.github/` and `.autoforge/`, to the
   repository's **default branch**.
2. Ensure GitHub Actions is enabled and the repository allows `GITHUB_TOKEN` to write repository
   contents.
3. Add repository secret `OPENAI_API_KEY` at
   **Settings → Secrets and variables → Actions → New repository secret**.

That is all. The initial upload itself triggers a setup/run attempt because the workflow watches its
core files. If the key is missing, it creates one setup issue (when Issues are enabled) and exits
safely. After the key exists, the next scheduled slot runs automatically; no manual dispatch is
required.

> ChatGPT subscriptions and OpenAI API billing are separate. Never place the key in a file or commit.

## Autonomous lifecycle

```text
GitHub schedule (~10 min)
        │
        ▼
load persistent state
        │
        ▼
select active project + task
        │
        ▼
GPT-5.6 Sol implementation worker
        │
        ▼
pre-validate every proposed file operation
        │
        ▼
apply bounded project-local candidate
        │
        ▼
secret/path/import/dependency/static scans
        │
        ▼
copy project to disposable test sandbox
        │
        ▼
compile + Ruff + offline Pytest + coverage
        │
        ├── fail → rollback + preserve repair feedback
        │
        ▼
independent GPT-5.6 Sol task review
        │
        ├── reject → rollback + retry next tick
        ├── continue → keep validated partial progress
        └── accept → advance roadmap
                         │
                         ▼
                 all tasks accepted?
                         │
                         ▼
               strict completion gate
                         │
                         ▼
             independent final audit
                  │              │
                revise          pass
                  │              │
             repair phase        ▼
                           archive project
                                  │
                                  ▼
                         start next project
```

## Quality-first defaults

- implementation worker: `gpt-5.6-sol`, reasoning `high`
- recovery worker after repeated difficulty: `gpt-5.6-sol`, reasoning `xhigh`
- independent task reviewer: `gpt-5.6-sol`, reasoning `xhigh`
- final scientific/software auditor: `gpt-5.6-sol`, reasoning `xhigh`
- novel-project planner: `gpt-5.6-sol`, reasoning `xhigh`
- bounded fallback: `gpt-5.6-terra`
- generated project coverage floor: **80%**
- final project requires executable source, at least **4 explicit tests**, substantial documentation,
  reproducibility/usage/limitations sections, and no unfinished implementation markers
- tests run with credentials scrubbed and sockets disabled, in a disposable copy of the project
- all model output uses strict structured JSON and is path/size/dependency constrained before write
- repeated quality/review failures persist precise repair feedback and automatically enter stronger
  recovery reasoning instead of blindly repeating the same work
- external API/install/push failures are surfaced through one operational GitHub Issue and retried by
  a later scheduled run
- pushes use bounded fetch/rebase/retry and never force-push
- the commit step rejects any autonomous working-tree change outside state/index, generated blueprint, and
  active/completed project paths, protecting the trusted control plane even if a generated test escapes
  its intended project directory

Repository variables can override model/reasoning choices without modifying source:
`FORGE_WORKER_MODEL`, `FORGE_REVIEWER_MODEL`, `FORGE_PLANNER_MODEL`, `FORGE_FALLBACK_MODEL`,
`FORGE_WORKER_REASONING_EFFORT`, `FORGE_RECOVERY_REASONING_EFFORT`,
`FORGE_REVIEWER_REASONING_EFFORT`, `FORGE_PLANNER_REASONING_EFFORT`.
Set `FORGE_ENABLED=false` to pause autonomous work.

## Research program

The seed catalog contains seven serious simulation-first projects. **Every seed and every dynamically
planned project must include all four core domains: AI/ML, robotics, data processing, and satellite
systems.** Remote sensing and orbital mechanics are added where useful.

1. Satellite-to-Rover Terrain Intelligence
2. Orbital Telemetry Anomaly Lab + Autonomous Inspection Decisions
3. Multispectral Change Detection + Ground-Robot Validation Planning
4. Satellite Attitude Estimation + Learned Sensor-Bias Modeling
5. Ground-Station Contact Scheduling + Robotic Antenna Simulation
6. Orbital Debris Conjunction Risk + Autonomous Avoidance Decision Support
7. Satellite-Prior Autonomous Mapping & Sensor Fusion

The seed program currently contains **75 bounded engineering tasks**. When those projects are
completed and independently audited, the planner creates the next 10–14 task project automatically.

## Safety and scientific scope

Generated projects are simulation/research software. Robotics/control outputs are decision-support or
simulation only; OrbitalForge is not permitted to generate weaponization, physical actuator control,
credentials, network-dependent tests, private mission data, or fabricated results. Generated code is
statically checked before execution, and model-produced file operations are restricted to the active
project directory.

Do not use generated results directly for safety-critical, spacecraft-command, navigation, medical,
financial, or other high-stakes decisions without independent domain validation.

## Repository layout

```text
.autoforge/state.json             versioned persistent state
catalog/projects.yml              seed research roadmaps
catalog/generated/                trusted persisted dynamic blueprints
config/forge.yml                  model, quality, budget and safety controls
projects/active/                  one active project
projects/completed/               final-gated + audited projects
src/orbitalforge/                 trusted orchestration engine
.github/workflows/autoforge.yml   autonomous scheduler/runner
.github/workflows/ci.yml          repository CI
PROJECTS.md                       generated program status/index
DEPLOYMENT.md                     operational deployment notes
ARCHITECTURE.md                   execution/state architecture
SECURITY.md                       trust boundaries and limitations
```

## Local verification

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
python -m pip install -e ".[dev]"
python -m compileall -q src tests
python -m ruff check src tests
python -m ruff format --check src tests
python -m pytest -q
python -m orbitalforge.cli validate --root . --all-projects
```

One manual local tick:

```bash
export OPENAI_API_KEY="..."
python -m orbitalforge.cli tick --root .
```

## Operational reality

The workflow requests a ten-minute cadence at `:07, :17, :27, :37, :47, :57` UTC. GitHub scheduled
workflows are **best-effort**, not a hard real-time scheduler: a run can start late, be queued behind a
previous run, or be affected by GitHub availability. OrbitalForge serializes runs deliberately to
prevent concurrent state corruption. Likewise, no software can guarantee availability of GitHub,
OpenAI, package indexes, network paths, billing, or repository permissions. The design therefore
focuses on rollback, persisted state, bounded retries, failure reporting, and safe automatic recovery.

See `DEPLOYMENT.md` before changing branch protection or Actions permissions.

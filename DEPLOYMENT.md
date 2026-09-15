# Deployment and operations

## Required one-time setup

1. Create or choose a GitHub repository and use its default branch (`main` is recommended).
2. Extract the final OrbitalForge ZIP and commit/upload **all** files and directories, including hidden
   `.github/` and `.autoforge/` directories, to that default branch.
3. Confirm **Settings → Actions → General** permits Actions for the repository and that workflow
   permissions allow `GITHUB_TOKEN` to write repository contents. The workflow requests only
   `contents: write` and `issues: write`.
4. Add repository secret `OPENAI_API_KEY` under
   **Settings → Secrets and variables → Actions → New repository secret**.

The initial upload changes core OrbitalForge paths and therefore triggers the workflow immediately.
If the secret is not present yet, the run only creates a setup issue and exits safely. After the key is
added, the next scheduled slot starts automatically.

## Schedule

The requested UTC slots are:

`07, 17, 27, 37, 47, 57` minutes past each hour.

This is a nominal ten-minute cadence. GitHub Actions scheduling is best-effort and may delay or queue
runs. `concurrency` serializes OrbitalForge runs so two workers never update persistent state at the
same time. A run has an 18-minute hard ceiling; if a run overlaps a later schedule, the later run waits
rather than racing it.

## Branch protection

OrbitalForge does not bypass branch protection, required reviews, rulesets, or repository governance.
If the default branch rejects direct writes from `GITHUB_TOKEN`, autonomous commits cannot be pushed.
Use a repository/policy where bot writes are intentionally permitted, or adapt the delivery strategy
to PR-based governance. Do not weaken unrelated production protections simply to run OrbitalForge.

## Optional repository variables

- `FORGE_ENABLED=false` pauses autonomous work.
- `FORGE_WORKER_MODEL`, `FORGE_REVIEWER_MODEL`, `FORGE_PLANNER_MODEL` override model IDs.
- `FORGE_FALLBACK_MODEL` overrides the bounded fallback model.
- `FORGE_WORKER_REASONING_EFFORT`, `FORGE_RECOVERY_REASONING_EFFORT`,
  `FORGE_REVIEWER_REASONING_EFFORT`, `FORGE_PLANNER_REASONING_EFFORT` override reasoning effort.

## Failure behavior

- Missing API key: one setup issue, no generated code.
- Invalid/unsafe/untested candidate: local rollback, repair feedback persisted, next tick retries.
- Repeated task difficulty: automatic recovery mode with stronger reasoning and prior gate feedback.
- Model/API/install failure: workflow fails; one operational issue is opened/refreshed; later schedule
  retries from the last committed state.
- Push race: bounded fetch/rebase/push retry; no force push.
- Final gate/audit revision: project stays active and enters a repair phase.
- Final audit pass: project moves to `projects/completed/`, then the next project starts automatically.

## Billing and quotas

The ten-minute cadence can make many model calls. OpenAI API billing, project limits, rate limits, and
model access belong to the API account associated with `OPENAI_API_KEY`. Monitor API usage and set
account-level limits appropriate to your budget. OrbitalForge records observed model token usage in
its persistent state and `PROJECTS.md`, but that telemetry is not a billing authority.

## Platform limits to monitor

For private repositories, GitHub-hosted runner minutes/storage are subject to the account's Actions
allowance and billing. Public-repository scheduling is also governed by GitHub's inactivity rules.
OrbitalForge cannot override platform quotas, a disabled Actions service, repository billing limits,
or external service outages; operational failures are surfaced and later schedules retry when the
platform permits.

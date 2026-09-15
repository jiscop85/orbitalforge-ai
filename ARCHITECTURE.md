# Architecture

OrbitalForge v3 is a durable state machine around bounded model calls. It deliberately separates
planning, implementation, deterministic validation, independent review, and final audit.

## State machine

The durable state lives in `.autoforge/state.json` (schema version 3). Important states are:

- `build`: execute the current roadmap task.
- `audit_pending`: all roadmap tasks are accepted; retry the final audit without inventing extra work.
- `final_review`: deterministic completion gate or final auditor requested specific repair work.
- completed: active directory is archived and the catalog index advances.

Rejected work records the failure/reviewer feedback so the next run does not repeat blindly. After
repeated attempts, the implementation worker enters `xhigh` recovery reasoning.

## Work-unit transaction

For each candidate, OrbitalForge:

1. obtains strict-schema file operations from the implementation model;
2. validates **all** paths, sizes, extensions and content before the first write;
3. records per-file backups and applies only project-local operations;
4. runs static secret/dependency/import/layout scans;
5. copies the complete active project into a disposable temporary directory;
6. executes compile, Ruff, Pytest with sockets disabled, and coverage inside that disposable copy
   with credential-like environment variables removed;
7. computes a bounded diff from the local backup set;
8. invokes an independent reviewer when the task claims completion or recovery requires review;
9. rolls back a rejected candidate, or persists accepted/validated progress and state.

No generated code is executed after the workflow introduces GitHub push credentials.

## Completion transaction

Once every task is accepted, the deterministic final gate requires source code, tests, documentation,
coverage, no unfinished markers, and explicit usage/reproducibility/limitations documentation. A
separate final model audit then checks scientific coherence, end-to-end integration, simulation-only
robotics scope, honest claims and reproducibility. Only a `pass` archives the project.

## Project generation

Seed projects are stored in `catalog/projects.yml`. When the catalog is exhausted, a planner produces
one strict-schema 10–14 task blueprint. The trusted engine persists each dynamic blueprint as a
separate ordered JSON file under `catalog/generated/`, avoiding unbounded growth of the state file. Validation rejects duplicate IDs, near-duplicate titles,
invalid task structures, or plans that omit any required core domain: **AI/ML, robotics, data
processing, satellite systems**.

## Concurrency and persistence

GitHub Actions uses one repository-scoped concurrency group with cancellation disabled. This favors
state consistency over starting overlapping workers. Changes are committed only after the engine has
returned successfully. Push credentials are configured only after generated tests have finished.

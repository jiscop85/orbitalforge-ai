# OrbitalForge maintainer instructions

- Preserve the state-machine invariants and backward-compatible state migration.
- Never allow model output to write outside the active project directory.
- Keep generated-code execution credential-free and isolated from push credentials.
- Do not weaken secret, dependency, network/process, test, coverage, or final-audit gates merely to
  make autonomous runs pass.
- New seed/dynamic projects must integrate all core domains: AI/ML, robotics, data processing, and
  satellite systems; robotics/control remains simulation/decision-support only.
- Every bug fix or orchestration change requires a regression test where practical.
- Prefer bounded deterministic behavior, rollback, idempotency and explicit failure over silent
  recovery that could corrupt state.
- Keep GitHub Actions versions current and deployment documentation aligned with actual behavior.

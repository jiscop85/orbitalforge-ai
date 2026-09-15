# OrbitalForge Ultimate v3.0.0 — release verification

Release target: GitHub-hosted autonomous research factory for AI/ML, robotics, data processing and
satellite systems.

Verified design properties:

- nominal ten-minute GitHub Actions schedule, offset from minute zero;
- default-branch-only autonomous operation with serialized concurrency;
- current GPT-5.6 Sol worker/reviewer/planner model IDs, Terra fallback;
- strict structured model outputs and bounded model/file/context budgets;
- persistent v3 state with legacy v2 migration;
- project-local prevalidated writes with rollback;
- generated-code secret/path/import/dependency controls;
- generated tests execute in a disposable project copy with secret-like environment variables removed
  and network sockets disabled;
- 80% generated-project coverage floor plus compile/Ruff/Pytest gates;
- independent task review and final scientific/software audit;
- durable repair/recovery mode for rejected or incomplete work;
- automatic archive and next-project transition;
- dynamic project planning after the seed catalog, with blueprints persisted as ordered files rather
  than growing the state document indefinitely;
- autonomous commit allowlist that rejects changes to trusted control-plane paths;
- no force-push and bounded rebase/push retry;
- operational GitHub Issue on external/infrastructure failure;
- GitHub Actions dependencies pinned to immutable release commit SHAs and maintained by Dependabot.

Required external condition: the repository owner must add `OPENAI_API_KEY` as a GitHub Actions secret
and the repository/account must have sufficient GitHub Actions and OpenAI API permissions, quota and
billing. GitHub scheduling and external APIs are not hard-real-time or 100%-available services; see
`DEPLOYMENT.md` and `README.md` for the exact operational guarantees and limitations.

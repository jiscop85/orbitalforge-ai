# Changelog

## 3.0.0 — Final hardened release

- Upgraded persistent state schema to v3 with migration from v2, rejection telemetry and model-usage
  counters.
- Added strict OpenAI Responses API structured outputs, prompt caching, bounded retry/fallback and
  stronger recovery reasoning.
- Added complete prevalidation of model file operations before any write.
- Moved generated project execution into disposable test copies with scrubbed credential environment
  and disabled sockets.
- Raised default generated-project coverage gate to 80% and strengthened final completion checks.
- Added recovery feedback persistence, `audit_pending`, final repair cycles and conservative archive
  semantics.
- Required all seed and dynamically generated projects to integrate AI/ML, robotics, data processing
  and satellite systems.
- Persisted dynamic blueprints as ordered files under `catalog/generated/` so indefinite operation does
  not inflate the state file with every future project definition.
- Expanded seed roadmaps with missing cross-domain integration work.
- Hardened GitHub workflow auth ordering, push race handling, operational failure Issues, initial
  upload trigger, and a final working-tree path allowlist that prevents autonomous commits to trusted
  control-plane files.
- Pinned `actions/checkout` to 7.0.1 and `actions/setup-python` to 7.0.0.
- Expanded regression tests for state migration, core-domain requirements, atomic prevalidation and
  symlink rejection.
- Updated deployment/security documentation to describe external-service and scheduling realities.

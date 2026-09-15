# Security model

OrbitalForge executes model-generated scientific Python, so the repository treats generated content
as untrusted until it passes bounded controls. These controls reduce risk; they are not a formal
security proof or a substitute for independent review of high-stakes software.

## Trust boundaries

Trusted control plane:

- `src/orbitalforge/`
- `.github/workflows/`
- `config/forge.yml`
- `catalog/projects.yml`
- `.autoforge/state.json` (written only by the trusted engine)

The model is allowed to request writes only inside `projects/active/<current-project>/`. Direct model
writes to `.github`, `.git`, `.autoforge`, `PROJECT.md`, `STATUS.md`, parent paths, credential-like
filenames, unsupported extensions, symlink escapes, or oversized files are rejected.

## Before generated code runs

OrbitalForge checks:

- likely API keys/private-key material and credential assignments;
- symlinks and unexpectedly large generated files;
- Python AST imports against an allow/deny policy;
- process/network/dynamic-execution primitives;
- project dependency manifests against an allowlist;
- file-operation count and byte budgets.

All operations are prevalidated before the first generated write, then backed up for rollback.

## Test isolation

Quality execution uses a disposable copy of the active project. Credential-like environment variables
(including the Groq key and GitHub tokens) are removed, a private temporary HOME/cache is used, and
Pytest sockets are disabled. Push credentials are not introduced into the workflow until all generated
code execution is finished.

This significantly reduces exposure but is not equivalent to a hardware/VM security boundary. As a
second boundary, the GitHub commit step refuses any autonomous working-tree change outside the
state/index, generated-blueprint, and active/completed-project allowlist. Do not add sensitive data to
generated project context. The intended environment is an ephemeral GitHub-
hosted runner and a repository containing no secret files.

## Domain restrictions

Generated projects are simulation/research only. The prompts and static policy prohibit credentials,
network-dependent tests, weaponization, physical actuator control, private mission data, and fabricated
scientific results. Outputs must not be used directly for real spacecraft/robot control or other
safety-critical decisions without independent expert validation.

## Secret handling

`GROQ_API_KEY` must exist only as a GitHub Actions repository/environment secret. Never commit API
keys, PATs, private keys, `.env` files or exported credentials. Secret-like generated content is
rejected by static scans and the commit step also blocks suspicious credential filenames.

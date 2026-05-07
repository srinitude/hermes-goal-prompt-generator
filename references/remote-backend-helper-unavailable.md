# Remote backend helper unavailable during goal prompt generation

When Hermes is running with a remote terminal backend (for example Daytona), the skill files shown in the prompt may live on the user's host path (for example `/Users/kiren/.hermes/skills/...`) while terminal execution happens inside the remote sandbox (for example `/root`). In that case direct commands such as:

```bash
python /Users/kiren/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py --json "..."
```

can fail because the skill directory is not mounted into the terminal backend, even though `skill_view()` can still read the skill and supporting files.

## Required workflow

1. Probe whether the skill directory and helper scripts exist in the execution backend before invoking them.
2. If the helper exists, use it normally.
3. If the helper is absent, do not stop and do not claim the generated artifacts are impossible. Use `skill_view()` to load the needed support files and reconstruct the generation/validation flow in the backend:
   - create `~/.hermes/goal-prompts/`,
   - write the optimized Markdown contract under that directory,
   - write a local validator if the packaged validator script is unavailable,
   - write the paired `<project>-<intent>-tdd-tasks.yaml`,
   - write or reconstruct the task-list structural validator,
   - install only minimal missing runtime dependencies needed for validation (for example `pyyaml`),
   - run both validators,
   - verify the handoff `/goal` line was not persisted into either artifact,
   - print exactly one final handoff `/goal` line.
4. Be explicit in the report that Firecrawl/opensrc or packaged helper validation was unavailable if those commands are missing in the backend; preserve the requirements as execution-time validation instead of claiming success.

## Observed Daytona example

A Daytona-backed session reported:

- execution cwd/home: `/root`
- OS: Debian 13 in Docker/Daytona
- skill directory `/Users/kiren/.hermes/skills/software-development/goal-prompt-generator` did not exist inside the sandbox
- `firecrawl`, `opensrc`, `pandoc`, and `wkhtmltopdf` were not installed
- `python3` existed but `PyYAML` was missing; installing `pyyaml` via `uv pip install --system pyyaml` enabled YAML validation

This is a backend-mount issue, not a reason to skip the goal-prompt-generator contract.
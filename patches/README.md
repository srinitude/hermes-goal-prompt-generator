# Patches

`hermes-agent-goal-preflight.patch` contains the Hermes Agent source changes needed to make raw built-in `/goal <text>` commands run `goal-prompt-generator` before goal execution.

Apply from a Hermes Agent checkout:

```bash
cd ~/.hermes/hermes-agent
git apply /path/to/goal-prompt-generator/patches/hermes-agent-goal-preflight.patch
```

Review the patch before applying. It touches CLI, gateway, TUI, goal-state persistence, and focused tests.

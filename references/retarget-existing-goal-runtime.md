# Retargeting an Existing Goal to a New Runtime Location

Use this when the user asks to update an already-generated goal prompt and paired task-list YAML so the real source/runtime locations move to a new environment (for example Daytona) without executing the goal.

## Pattern

1. Treat the Markdown goal as the immutable contract for future execution, but patch it in place when the current user explicitly asks to update the contract itself.
2. Treat the paired YAML as runtime state plus contract metadata. For ordinary execution mutate only per-task `status`, `learnings`, and `gotchas`; for an explicit retargeting request, update only the location-bearing contract fields needed to make the runtime/source paths truthful.
3. Do not execute the printed `/goal` handoff or start GREEN/production work while retargeting. This is goal maintenance, not goal execution.
4. Replace every stale environment reference consistently across duplicated sections such as `Goal`, `Original Intent`, assumptions, hard invariants, context files, validation steps, gotchas, and resume points.
6. If the user says credentials or mounts were added after a blocked run, re-probe inside the execution backend before resuming. For Daytona, check process env and `/root/.hermes/.env` for key presence only, then prove `/root/.hermes` is a real mounted/synced Hermes home with `findmnt -T /root/.hermes` and `/proc/self/mountinfo`; path existence alone is not proof.

## Verification

Run both validators after retargeting:

```bash
python3 -c "import sys, pathlib; sys.path.insert(0, '/root/.hermes/skills/software-development/goal-prompt-generator/src'); from goal_prompt_generator.validation import validate_optimized_markdown; r = validate_optimized_markdown(pathlib.Path('<goal.md>').read_text()); print('valid:', r.valid, 'reasons:', r.reasons); sys.exit(0 if r.valid else 1)"
python3 /root/.hermes/skills/software-development/goal-prompt-generator/scripts/validate_task_list_yaml.py <tasks.yaml>
```

Then run stale-reference checks for the old environment names/paths, and remote-backend mount/credential checks when applicable, for example:

```bash
python3 - <<'PY'
from pathlib import Path
for path in [Path('<goal.md>'), Path('<tasks.yaml>')]:
    text = path.read_text()
    print(path.name, {'/Users/kiren': text.count('/Users/kiren'), 'local Mac': text.count('local Mac'), 'macOS': text.count('macOS')})
PY
python3 - <<'PY'
import os
from pathlib import Path
keys = ['GOOGLE_GENERATIVE_AI_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_API_KEY', 'VENICE_API_KEY', 'DAYTONA_API_KEY', 'FIRECRAWL_API_KEY']
print({'process_env': {k: bool(os.environ.get(k)) for k in keys}})
env = Path('/root/.hermes/.env')
found = set()
if env.exists():
    for line in env.read_text(errors='ignore').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            found.add(line.split('=', 1)[0])
print({'env_file_exists': env.exists(), 'env_key_presence': {k: k in found for k in keys}})
PY
findmnt -T /root/.hermes || true
awk 'tolower($0) ~ /hermes|daytona|workspace|volume/ {print}' /proc/self/mountinfo | sed -n '1,80p'
```

Report validation results, stale-reference counts, and whether credentials/mounts are actually visible in the execution backend. If the source/runtime paths, required tools, secrets, or host/volume mount are missing in the new environment, mark only the appropriate analysis/readiness task as blocked and record an exact resume point rather than fabricating runtime evidence from upstream source.

## Daytona Mastra Example

For Mastra memory goal retargeting, the canonical Daytona paths were:

- Source repo: `/root/hermes-setup/memory/hermes-mastra`
- Hermes runtime checkout: `/root/.hermes/hermes-agent`
- Active plugin: `/root/.hermes/hermes-agent/plugins/memory/mastra`
- Profile/memory state: `/root/.hermes`

If those paths do not exist, the correct outcome is a blocked analysis/readiness task with explicit blockers such as missing `hermes`, `claude`, `bun`, source repo, runtime checkout, or plugin path.
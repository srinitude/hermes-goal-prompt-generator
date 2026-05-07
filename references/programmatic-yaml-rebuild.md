# Programmatic YAML rebuild + bulk Markdown augmentation

When the helper-generated baseline is structurally valid but semantically thin (the canned 7-task scaffold), the right move is to **rewrite the YAML from a Python dict** and **bulk-augment the Markdown via a single `replace`-pass script**, not via dozens of serial patch calls.

## When this applies

- The user's prompt is short ("fix mastra memory") but the implied scope is large (multi-component refactor, multiple repos, SLOs, multi-workspace, etc.).
- The helper emitted valid Markdown + YAML, both pass their validators, but a downstream coding agent would not be able to execute the YAML because tasks are placeholder-shaped.
- You need 30–50+ tasks across ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR with shared rule blocks referenced by id.

## Pattern: rebuild YAML from a Python dict

Don't try to `mcp_patch` a generated YAML into shape. The helper's generic 7-task scaffold has the wrong field set per task to be patched into a domain-rich plan; you'll fight the validator and produce a fragile diff. Instead:

1. Write `/tmp/build_yaml.py` that constructs the full task list as a Python dict — `STYLEGUIDE`, `GUARDRAILS`, `CI_COMMANDS`, `PRINCIPLES` (all 18, named per `tasklist.PRINCIPLES`), `ANALYSIS`/`BOOTSTRAP`/`RED`/`GREEN`/`REFACTOR` task lists, `agent_runtime_protocol`, `coding_agent_execution_contract`.
2. Use a `task(...)` helper that returns the full per-task dict with every required field present (`prerequisites`, `dependencies`, `blocking_tasks`, `validation_steps`, `ci_commands`, `styleguide_rules`, `guardrails`, `learnings: []`, `gotchas: []`, `context_files`, `context_urls`, `principle_ids`).
3. Add two assertions before writing:
   - every declared `P*` principle id appears in some task's `principle_ids` (validator enforces this);
   - every GREEN task has at least one RED task in `dependencies` ∪ `prerequisites` (validator enforces this).
4. `yaml.safe_dump(data, sort_keys=False, allow_unicode=True)` and write to the same path the helper produced (overwrite is fine — the YAML is runtime state).
5. Run `scripts/validate_task_list_yaml.py <path>`.

This was ~5 minutes for a 48-task plan. Patching would have been an hour and produced a worse plan.

### Per-task density tip

`coding-agent-task-list-yaml.md` says "tasks reference the shared blocks by id, not by repeating prose" — follow that. A task entry should be ~15–25 lines of YAML, not 60. If a task is hitting 60 lines, you're inlining what belongs in a shared block. Pull it up to `styleguide_rules` / `guardrails` / `ci_commands` and reference the id.

### `coding_agent_execution_contract` requires a `rule` paragraph (easy to miss)

`scripts/validate_task_list_yaml.py` (lines ~333-335) explicitly requires `coding_agent_execution_contract.rule` to be a non-empty string:

```python
rule = contract.get("rule")
if not (isinstance(rule, str) and rule.strip()):
    problems.append("coding_agent_execution_contract.rule: missing or empty")
```

When rebuilding from a Python dict, it's tempting to populate only `executor`, `required_flags`, `canonical_invocation`, and `forbidden_alternatives` (those four are the more obviously named fields). The validator will then emit `FAIL: coding_agent_execution_contract.rule: missing or empty` and you'll have to amend. Pre-empt it: include a `rule` field whose value is the same `CLAUDE_CLI_EXECUTION_CONTRACT` paragraph that lives in the goal Markdown (or build it from `REQUIRED_FLAGS` with `", ".join(f"`{n} {p}`" for n, p in REQUIRED_FLAGS)` interpolation so it never drifts from the flag list).

Cross-check shape: the helper-emitted YAMLs in `~/.hermes/goal-prompts/*-tdd-tasks.yaml` from prior runs always carry `rule` near the top of the contract block — match that order.

### Pre-write assertions that catch real defects

Before `yaml.safe_dump`, run the two enforcement assertions documented in the main pattern (`assert_principle_coverage`, `assert_green_has_red_ancestor`). The second one catches a common mistake: when a GREEN task's *only* ancestors are other GREEN tasks (for example `G07` depending solely on `G01..G06`), it has no RED task in its `dependencies ∪ prerequisites` *direct* set, and `validate_task_list_yaml.py` rejects it. Fix by adding `R00` to both `prerequisites` and `dependencies` of every standalone GREEN task that doesn't already cite a specific RED test. Cheap and deterministic — caught 5 such defects in one rebuild pass during a real session.

### Honest unavailability shape

When Firecrawl/opensrc are unavailable in the execution backend, the helper writes empty `validation_evidence.firecrawl.required_maps_present: {}` and empty `opensrc.fetched: {}`. The validator accepts this only when `auth: unavailable` / `cli_version: unavailable`. Keep those literals exact, then add a sibling `execution_time_required` array enumerating every map target / repo with the canonical command template. The validator does NOT enforce `execution_time_required`'s shape, but the downstream coding agent does — keep it concrete (templates: `firecrawl map <url> --limit 5000 --json --pretty`, `firecrawl scrape <url> --format markdown --json`, `opensrc fetch <org>/<repo>` with a `list_probe_command` fallback per `references/research-tool-readiness.md`).

## Pattern: bulk Markdown augmentation via single `mcp_execute_code` pass

`mcp_patch` against a generated goal Markdown file currently exhibits a **post-write verifier flake**: the verifier reports `wrote N chars, read back N+1` and returns `success=false` even when the patch landed correctly on disk. Confirmed by `wc -c` + `grep` after the "failure": the new content IS present. The 1-byte diff appears to be a trailing-newline / final-`\n` accounting issue in the verifier path, not a real write failure.

The skill's own loop-detection warning fires after three failed patches in a row, so naive serial patching of 8 sections will burn three retries before you switch strategies anyway.

**Workaround that worked end-to-end**: write `/tmp/augment.py` that does ONE pass:

```python
import pathlib
p = pathlib.Path("<generated-goal>.md")
text = p.read_text()
replacements = [
    ("<unique anchor 1>", "<replacement 1>"),
    ("<unique anchor 2>", "<replacement 2>"),
    # ...
]
for old, new in replacements:
    if old not in text:
        print(f"MISSING: {old[:80]}…")
        continue
    text = text.replace(old, new, 1)
p.write_text(text)
```

Then immediately re-run `validate_optimized_markdown` to confirm every required section, the autonomy/non-execution/isolation/cleanup paragraphs, and every `claude` CLI flag still appear verbatim. Substring-match validators are the safety net here — they catch the case where a thin canned section was replaced with prose that accidentally dropped a required substring.

### Anchors must be unique

The helper's generic Phase descriptions (`### Phase 0: BOOTSTRAP\n\nValidate context, prerequisites, source materials, environment, and local quality gates before making changes.`) are unique enough to anchor a `replace(..., 1)`. The boilerplate paragraphs (autonomy, non-execution, isolation, software constraints, cleanup, engineering principles, claude CLI contract) are NOT — they appear in dozens of generated files and should never be the anchor. Keep anchors scoped to the per-goal text; never anchor on substring-matched boilerplate.

### Why this is faster than `mcp_patch`

For 8 section replacements:

- 8 × `mcp_patch` calls @ ~2s each + one verifier flake retry every ~3 calls ≈ 25–30s + risk of triggering the same-tool-failure loop warning at call 3.
- 1 × `mcp_execute_code` pass ≈ 2s, with explicit per-anchor `MISSING` reporting in one shot.

## Pitfalls

1. **Accepting a semantically generic helper output because it validates.** A valid Markdown/YAML pair can still be unusable when the helper names it something like `isolated-optimized-goal-contract-paired-*`, emits a canned title, or leaves the task list as the generic 7-task scaffold. Treat that as a semantic failure, not success. Rebuild both artifacts under meaningful filenames from the original prompt, rerun both validators, verify no `/goal` line was persisted, and delete the abandoned generic artifacts plus any raw prompt scratch file before reporting.
2. **Trying to `mcp_patch` the entire helper-generated YAML.** Don't. Rewrite from a Python dict. The helper's task scaffold has the wrong field shape (task fields are correct in count but the content is generic) — patch-shaped surgery on it produces a worse plan than a clean rebuild.
3. **Serial-patching the Markdown after seeing a "verification failed" error.** Re-read the file with `wc -c` + `grep` first. If the patch landed, treat the verifier message as a flake and continue. After the third "failure" in a row you'll trip the same-tool-failure loop warning anyway — pre-empt it by switching to the bulk-rewrite script before the 4th attempt.
4. **Inlining shared rules in every task.** Validator passes either way, but the YAML triples in size and patches become impossible. Pull every repeated rule into `styleguide_rules` / `guardrails` / `ci_commands` and reference by id (e.g. `S1_file_size`, `G3_red_hard_gate`, `CC_TEST_RECALL_SLO`).
5. **Forgetting that the validator requires every declared `P*` principle to be referenced in some task.** When you cherry-pick principles per task, run a `set(PRINCIPLES) - used` assertion before writing the YAML, or add an `X02` rubric-replay task whose `principle_ids` is the full P1..P18 list (cleanest catch-all).
6. **Using naive substring checks for leaked secrets.** Short provider prefixes such as `sk-` can appear harmlessly inside ordinary prose (`task-list`). Use regexes with realistic token lengths (for example `sk-[A-Za-z0-9_-]{20,}`, `AIza[0-9A-Za-z_-]{20,}`, `fc-[A-Za-z0-9_-]{20,}`, `ghp_[A-Za-z0-9_]{20,}`) before claiming generated artifacts contain secret-like values.
7. **Passing the handoff `/goal` line back into Hermes.** Per SKILL.md pitfall 21 it's a paste-target only. After the rebuild, just print it once in the chat report and stop — never feed it back into a goal-runner during the same skill turn.

# Programmatic YAML rebuild + bulk Markdown augmentation

When the helper-generated baseline is structurally valid but semantically thin (the canned 7-task scaffold), the right move is to **rewrite the YAML from a Python dict** and **bulk-augment the Markdown via a single `replace`-pass script**, not via dozens of serial patch calls.

## When this applies

- The user's prompt is short ("fix mastra memory") but the implied scope is large (multi-component refactor, multiple repos, SLOs, multi-workspace, etc.).
- The helper emitted valid Markdown + YAML, both pass their validators, but a downstream coding agent would not be able to execute the YAML because tasks are placeholder-shaped.
- You need 30–50+ tasks across ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR with shared rule blocks referenced by id.

## Pattern: rebuild YAML from a Python dict

Don't try to `mcp_patch` a generated YAML into shape. The helper's generic 7-task scaffold has the wrong field set per task to be patched into a domain-rich plan; you'll fight the validator and produce a fragile diff. Instead:

1. Write `/tmp/build_yaml.py` that constructs the full task list as a Python dict — `STYLEGUIDE`, `GUARDRAILS`, `CI_COMMANDS`, `PRINCIPLES` (all 18, named per `tasklist.PRINCIPLES`), `ANALYSIS`/`BOOTSTRAP`/`RED`/`GREEN`/`REFACTOR` task lists, `agent_runtime_protocol`, `coding_agent_execution_contract`.
2. Use a `task(...)` helper that returns the full per-task dict with every required field present (`dependencies`, `validation_steps`, `ci_commands`, `styleguide_rules`, `guardrails`, `learnings: []`, `gotchas: []`, `context_files`, `context_urls`, `principle_ids`) and never emits legacy graph fields (`prerequisites`, `blocking_tasks`).
3. Add two assertions before writing:
   - every declared `P*` principle id appears in some task's `principle_ids` (validator enforces this);
   - every GREEN task has at least one RED task in `dependencies` (validator enforces this).
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

Before `yaml.safe_dump`, run the two enforcement assertions documented in the main pattern (`assert_principle_coverage`, `assert_green_has_red_ancestor`). The second one catches a common mistake: when a GREEN task's *only* ancestors are other GREEN tasks (for example `G07` depending solely on `G01..G06`), it has no RED task in its `dependencies` *direct* set, and `validate_task_list_yaml.py` rejects it. Fix by adding `R00` to `dependencies` of every standalone GREEN task that doesn't already cite a specific RED test. Cheap and deterministic — caught 5 such defects in one rebuild pass during a real session.

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

The helper's generic Phase descriptions (`### Phase 0: BOOTSTRAP\n\nValidate context, required source materials, environment, and local quality gates before making changes.`) are unique enough to anchor a `replace(..., 1)`. The boilerplate paragraphs (autonomy, non-execution, isolation, software constraints, cleanup, engineering principles, claude CLI contract) are NOT — they appear in dozens of generated files and should never be the anchor. Keep anchors scoped to the per-goal text; never anchor on substring-matched boilerplate.

### `replace_section` helpers MUST be heading-level-aware

A natural shape for the bulk-augment pass is a `replace_section(text, start_marker, new_section)` helper that finds `start_marker` and replaces up to the *next* heading. The trap: a naive implementation that searches for `\n## ` (top-level only) works fine for `## Goal`, `## Scope`, `## Acceptance Criteria`, etc., but **silently swallows three subsections at once when applied to `### Phase 0: BOOTSTRAP`** — because the next `\n## ` hit is `## Software Development Constraints`, not `### Phase 1: RED`. The first cell crashes a few replacements later with `ValueError: substring not found` when it tries to anchor on `### Phase 1: RED\n` (already deleted with the BOOTSTRAP body).

Right shape — pass the heading level explicitly:

```python
import re
def replace_until_next_heading(text, start_marker, new_section, level="##"):
    """Replace from start_marker until the next heading at the same level or higher."""
    idx = text.index(start_marker)
    rest = text[idx + len(start_marker):]
    if level == "##":
        m = re.search(r"\n## ", rest)        # only top-level
    else:  # "###"
        m = re.search(r"\n##(?:#)? ", rest)  # ## or ### — whichever comes first
    if not m:
        return text[:idx] + new_section + "\n"
    after = idx + len(start_marker) + m.start()
    return text[:idx] + new_section + "\n" + text[after+1:]
```

Call it with `level="##"` for top-level sections (`## Goal`, `## Scope`, `## Acceptance Criteria`, `## Validation Commands`, `## Completion Definition`, `## Failure Conditions`, `## Final Output Requirements`) and `level="###"` for the four phase subsections (`### Phase 0: BOOTSTRAP`, `### Phase 1: RED`, `### Phase 2: GREEN`, `### Phase 3: REFACTOR`).

Recovery rule when the partial-edit cell crashes: the helper is idempotent given the same prompt + `--workdir` + `--json`. Cleanest reflex is `GOAL.unlink(); TDD.unlink()` then re-run the helper for a fresh ~2 s baseline, and re-apply the entire bulk pass with the level-aware helper. Half-edited Markdown is faster to throw away than to repair by hand.

### Why this is faster than `mcp_patch`

For 8 section replacements:

- 8 × `mcp_patch` calls @ ~2s each + one verifier flake retry every ~3 calls ≈ 25–30s + risk of triggering the same-tool-failure loop warning at call 3.
- 1 × `mcp_execute_code` pass ≈ 2s, with explicit per-anchor `MISSING` reporting in one shot.

## Pitfalls

1. **Accepting a semantically generic helper output because it validates.** A valid Markdown/YAML pair can still be unusable when the helper names it something like `isolated-optimized-goal-contract-paired-*`, emits a canned title, or leaves the task list as the generic 7-task scaffold. Treat that as a semantic failure, not success. Rebuild both artifacts under meaningful filenames from the original prompt, rerun both validators, verify no `/goal` line was persisted, and delete the abandoned generic artifacts plus any raw prompt scratch file before reporting.

   **Rename-and-recover pattern (when the helper has already written generic-named files):** the helper's `--input-file` path triggers a regeneration that often suffixes a `-2` to avoid collision and emits filenames like `<title>-goal-2.md` and **`<title>-goal-2.md-tdd-tasks.yaml`** — the YAML name picks up the Markdown's `.md` extension as part of its stem (real bug observed in v1.6.0 generation). Recovery before the heavy rebuild:
   ```bash
   cd ~/.hermes/goal-prompts && \
     rm -f <generic-title>-goal.md <generic-title>-tdd-tasks.yaml && \
     mv <generic-title>-goal-2.md <project>-<intent>-goal.md && \
     mv "<generic-title>-goal-2.md-tdd-tasks.yaml" <project>-<intent>-tdd-tasks.yaml
   ```
   Then read the renamed Markdown, patch its `# Generated Goal Title` line + the `## Research and Source Validation Requirements` body inline (don't regenerate via the helper — you'll just get another generic title), re-run `validate_optimized_markdown` to confirm the patch landed, and proceed straight to the Python-dict YAML rebuild against the renamed YAML path. This avoids burning a second helper round-trip on the same prompt.
2. **Trying to `mcp_patch` the entire helper-generated YAML.** Don't. Rewrite from a Python dict. The helper's task scaffold has the wrong field shape (task fields are correct in count but the content is generic) — patch-shaped surgery on it produces a worse plan than a clean rebuild.
3. **Serial-patching the Markdown after seeing a "verification failed" error.** Re-read the file with `wc -c` + `grep` first. If the patch landed, treat the verifier message as a flake and continue. After the third "failure" in a row you'll trip the same-tool-failure loop warning anyway — pre-empt it by switching to the bulk-rewrite script before the 4th attempt.
4. **Inlining shared rules in every task.** Validator passes either way, but the YAML triples in size and patches become impossible. Pull every repeated rule into `styleguide_rules` / `guardrails` / `ci_commands` and reference by id (e.g. `S1_file_size`, `G3_red_hard_gate`, `CC_TEST_RECALL_SLO`).
5. **Forgetting that the validator requires every declared `P*` principle to be referenced in some task.** When you cherry-pick principles per task, run a `set(PRINCIPLES) - used` assertion before writing the YAML, or add an `X02` rubric-replay task whose `principle_ids` is the full P1..P18 list (cleanest catch-all).
6. **Using naive substring checks for leaked secrets.** Short provider prefixes such as `sk-` can appear harmlessly inside ordinary prose (`task-list`). Use regexes with realistic token lengths (for example `sk-[A-Za-z0-9_-]{20,}`, `AIza[0-9A-Za-z_-]{20,}`, `fc-[A-Za-z0-9_-]{20,}`, `ghp_[A-Za-z0-9_]{20,}`) before claiming generated artifacts contain secret-like values.
7. **Passing the handoff `/goal` line back into Hermes.** Per SKILL.md pitfall 21 it's a paste-target only. After the rebuild, just print it once in the chat report and stop — never feed it back into a goal-runner during the same skill turn.
8. **Treating `principles[]` as a Python list and indexing with `[0]`.** The helper's `tasklist.write_task_list` emits `principles` as a **dict** keyed `{P1: "…", P2: "…", …}`, NOT a list of `{id, text}` records. `y["principles"][0]` raises `KeyError: 0`; `for p in y["principles"]: p["id"]` raises `TypeError: string indices must be integers`. When trimming unused principles (Pitfall #5), filter the dict: `y["principles"] = {k: v for k, v in y["principles"].items() if k in used_ids}`. The structural validator accepts both shapes for read but the helper writes the dict shape, so the rebuild must round-trip the dict shape too.
9. **Helper auto-declares all 18 `P*` principles even when the goal genuinely only exercises a subset.** A small linter-add or doc-edit goal often uses only 8–12 principles across its tasks. The validator then fails with `principles: unused ids ['P5', 'P6', 'P7', 'P8', 'P13', 'P15', 'P16']`. Two remediations, both honest:
   - **Trim** `y["principles"]` to the in-scope subset before writing (preferred when the Markdown's `## Software Engineering Core Principles` section already enumerates all 18, satisfying the SKILL.md substring contract independently). Compute `used = {pid for ph in y["phases"] for t in ph["tasks"] for pid in t["principle_ids"]}` then `y["principles"] = {k: v for k, v in y["principles"].items() if k in used}`.
   - **Add** an X-phase rubric-replay task whose `principle_ids` is the full `P1..P18` list (cleanest catch-all when the goal is large enough to plausibly touch every principle). Pitfall #5 of this reference covers this option.
   The Markdown side is governed by the SKILL.md substring validator and is independent — the YAML's `principles[]` keys only need to be the ones some task references.
10. **`validation_reconciliation.resolutions` must be a verbatim copy of `conflicts`, not a parallel "outcome rows" array.** The structural validator (`scripts/validate_task_list_yaml.py` line ~157) checks `buckets["resolutions"] != buckets["conflicts"]` and emits `FAIL: validation_reconciliation.resolutions: must preserve conflicts ordering` whenever the two lists differ in any way — same length, same order, *same prose*. The natural reading of the field name plus the SKILL.md / `references/contrarian-validation.md` wording ("preserves the same ordering for end-to-end traceability", each entry carries `check_id`/`evidence_target`/`original_claim`/`contrarian_observation`/`severity`/`resolution`) suggests `resolutions[]` should be a parallel array recording the *outcome* per conflict (e.g. shorter `original_claim`, terminal `resolution` literal). It is not. The validator wants `resolutions == conflicts` element-for-element. When rebuilding from a Python dict, build the `conflicts` list once with the full prose and the chosen `resolution` literal already populated, then assign `data["validation_reconciliation"]["resolutions"] = list(data["validation_reconciliation"]["conflicts"])` (or `copy.deepcopy(...)` if any downstream code may mutate one of the lists). Don't waste time crafting a separate "shorter outcome row" view — the validator will reject it as ordering drift even when the order is identical. This is the most likely first failure on any clean rebuild that doesn't crib from a previously-helper-emitted YAML.

11. **Optional GREEN tasks (e.g. a one-line README cross-reference, a doc tweak) get rebuilt with no RED ancestor and the validator rejects them.** When you mark a task as "optional" or "skippable" in the goal Markdown, it's tempting to wire it only to a sibling GREEN task (e.g. `G07` deps `[G00]`) because the test side feels unnecessary. The validator enforces "every GREEN has at least one RED in `dependencies`" *unconditionally* — optional doesn't get a pass. Either (a) wire the optional GREEN to the most-relevant existing RED test (e.g. the AGENTS.md heading test `R02` for a README-cross-reference task, since the README change must not invalidate the heading assertion), or (b) drop the optional task entirely and let the user request it as a follow-up. Don't try to special-case it in the validator — the rule exists to keep the TDD discipline honest.

12. **Atomic `.tmp` write is correct, but the parse-back assertions block crashes on a forward-referenced helper, so `tmp.replace(YAML_PATH)` never runs and a stale `.yaml.tmp` is left on disk.** The atomic write pattern (`tmp = YAML_PATH.with_suffix('.yaml.tmp'); tmp.write_text(yaml.safe_dump(...)); re_data = yaml.safe_load(tmp.read_text()); <assertions>; tmp.replace(YAML_PATH)`) is the right shape for surviving the `mcp_patch` flake. The trap: if any assertion before the `tmp.replace()` line throws — most commonly `NameError` because a helper function (`task_for`, `phase_for`) is defined *after* the assertion that uses it, or a `KeyError` because the dict shape drifted — the script terminates with the live YAML untouched and a stale `.yaml.tmp` sibling on disk. The next run sees the original file and the rewrite is silently lost. Pre-empt it: define EVERY helper function at the top of the script, BEFORE any mutation or assertion. After any failed run, `ls /Users/$USER/.hermes/goal-prompts/*.yaml.tmp` and `rm` any leftovers before retrying. Confirmed on a real session: the script wrote the correct content to `.yaml.tmp` (24KB delta), `NameError: task_for` fired on the first assertion, `tmp.replace()` never executed, the live YAML stayed at the pre-edit size for the next half-hour until a `ls -la` caught the stale `.tmp`.

13. **Confusing skill-authoring-time deliverables with skill-execution-time deliverables in the TDD task list.** When the goal is "author a skill that, at runtime, writes per-product files to `~/.hermes/<slug>/<artifact>.yaml`", the helper sometimes emits a YAML where an ANALYSIS task's `validation_steps[]` cites the slug-bound runtime path as the authoring deliverable. That conflates two timelines: the authoring task (now) cannot substitute `<slug>` because no concrete product exists; the slug-bound path is a deliverable of the AUTHORED skill (later, when a real spec arrives). Symptom: an early ANALYSIS task gets stuck at `status: blocked` with a "no concrete spec supplied" gotcha, blocking the entire phase walk on user input. Right fix per pitfall #1 (in-place edit on a valid generated artifact): re-point the validation step at a slug-free authoring-time baseline, e.g. `~/.hermes/<run-namespace>/_baseline/<artifact>-contract.yaml`, AND record the disambiguation in the task's `learnings[]` so the historical context survives. The slug-bound path stays in the contract — it just gets correctly attributed to the authored skill's runtime, NOT to the authoring task. Add a `validation_reconciliation.conflicts[]` entry with severity `error` and resolution `corrected_in_yaml`, plus `resolutions = copy.deepcopy(conflicts)` per pitfall #10. `metadata.generated_at` and `metadata.source_prompt_hash` stay unchanged — same intent, same contract identity. Heuristic: if a `<...>` placeholder in `validation_steps[]` substitutes from runtime input that hasn't been provided yet, the step is in the wrong phase. Move it forward to GREEN (where the authored skill's runtime script does the substitution) or split the step in two: an authoring-time slug-free baseline + a runtime slug-bound output.

14. **Helper's `--json` payload returns `markdown_path: None`, `task_list_yaml_path: None`, `validation_status: None`, `yaml_validation_status: None` even though the artifacts wrote correctly to disk.** Observed on a v1.6.0 helper run with `--workdir <opensrc-cache-repo>`: `returncode == 0`, `status: generated`, `title` and `source_prompt_hash` populated, but the four path/validation fields all came back null. The artifacts WERE written under `~/.hermes/goal-prompts/<title-slug>-goal.md` and `<title-slug>-tdd-tasks.yaml`. Don't waste time re-running the helper with different flags. Recovery: `ls -la ~/.hermes/goal-prompts/<first-few-slug-words>*` (or grep the source hash through the existing `*.md` frontmatter), then run `validate_optimized_markdown` and `scripts/validate_task_list_yaml.py` directly against the located paths to confirm the helper actually did its job. Then proceed straight to the programmatic YAML rebuild against the located YAML path. The handoff `/goal …` line in the JSON payload's `handoff_prompt` field still references the correct absolute paths, which is the easiest way to recover the slug if `ls` is ambiguous.

15. **Probe the helper baseline's `principles{}` key shape AND `metadata.hard_invariants` type BEFORE writing any new task or rule.** Two confirmed shape ambiguities in helper-emitted YAMLs that bite scope-extension passes (pitfall #36 in SKILL.md):

    **Shape A — `principle_ids` keys: bare vs slug.** Several skill references show example principle ids in slug form (`P1_descriptions_before_execution`, `P10_data_validation_at_boundaries`, `P18_provider_specific_behind_contracts`) — that's the documented mnemonic shape used in prose. The helper's actual emitted `principles{}` dict in a real YAML uses BARE ids (`P1`, `P2`, ..., `P18`). The structural validator does a literal `set(task.principle_ids) <= set(principles.keys())` check, so a scope-extension task wired with slug-shaped ids fails as `bad principle_ids ref 'P10_data_validation_at_boundaries'` for every new task. One real session produced 33 such FAILs in a single rebuild before remap. Pre-empt:

    ```python
    import yaml
    p = yaml.safe_load(open(YAML_PATH).read())
    print('principle keys:', list(p.get('principles', {}).keys()))
    # If output is ['P1','P2',...,'P18'], use bare ids in new tasks.
    # If output is ['P1_descriptions_before_execution',...], use slug ids.
    # Don't mix — the structural validator rejects any unknown id verbatim.
    ```

    Recovery without a re-rebuild (one-cell remap):

    ```python
    remap = {  # only the slugs you actually used in the new tasks
        'P1_descriptions_before_execution': 'P1',
        'P10_data_validation_at_boundaries': 'P10',
        # ...
    }
    new_ids = {'A80','A81','A82','R80','R81','R82','R83','R84','G80','G81','G82','G83','G84','G85','X80'}
    for ph in data['phases']:
        for t in ph['tasks']:
            if t['id'] in new_ids:
                t['principle_ids'] = [remap.get(x, x) for x in t.get('principle_ids', [])]
    ```

    **Shape B — `metadata.hard_invariants` is `list` OR `dict`.** The helper baseline can emit `metadata.hard_invariants` as a `list` of "key: value" prose strings OR as a `dict` of `{key: value}` literal records, depending on the goal Markdown's hard-invariants block shape. The structural validator accepts both. Patch code that does `hi[:3]` (peek) hits `TypeError: unhashable type: 'slice'` against the dict shape; patch code that does `hi.append(<rule>)` hits `AttributeError: 'dict' object has no attribute 'append'` against the dict shape. Probe before mutating:

    ```python
    hi = data['metadata']['hard_invariants']
    if isinstance(hi, dict):
        hi['new_invariant_key'] = True   # or string value, or list value
        hi['fixed_account'] = 'kiren@fantasymetals.com'
    elif isinstance(hi, list):
        hi.append('new_invariant_key: true')
        hi.append('fixed_account: kiren@fantasymetals.com')
    else:
        raise AssertionError(f'unexpected hard_invariants shape: {type(hi).__name__}')
    ```

    Same general rule applies to `validation_evidence.repository_context.key_paths` (always a list of strings in current helper output) and `validation_evidence.firecrawl.required_maps_present` (always a dict of `{tech_name: {file, url_count, map_command, map_limit}}` records) — but re-probe each time, because the helper has shifted shapes between minor versions before. The cost of one probe cell is ~50ms; the cost of a `TypeError`/`AttributeError` mid-rebuild is a stale `.yaml.tmp` (pitfall #12) and a re-do of the whole rule-block addition.

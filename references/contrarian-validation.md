# Contrarian recheck-and-reconcile (goal-prompt-generator 1.4.0)

After the optimistic generator populates `validation_evidence`, run a second pass that assumes each claim is wrong until independently rechecked. Write the reconciled result into the YAML before printing the final `/goal` handoff. Do not emit sidecar JSON; the YAML is the runtime state.

## YAML block

Every `<project>-<intent>-tdd-tasks.yaml` with non-empty `validation_evidence.firecrawl` or `validation_evidence.opensrc` must carry:

```yaml
validation_reconciliation:
  conflicts:
    - check_id: firecrawl_map
      evidence_target: firecrawl
      original_claim: "url_count=5000"
      contrarian_observation: "firecrawl map observed url_count=0"
      severity: error
      resolution: escalated_as_execution_time_required
  resolutions:
    - check_id: firecrawl_map
      evidence_target: firecrawl
      original_claim: "url_count=5000"
      contrarian_observation: "firecrawl map observed url_count=0"
      severity: error
      resolution: escalated_as_execution_time_required
  final_state: some-claims-escalated-to-execution-time
```

`conflicts` and `resolutions` are the same ordered list of serialized `Conflict` dictionaries. The duplication is intentional for consumers that read either key.

## Dataclasses

```python
@dataclass
class Conflict:
    check_id: str = ""
    evidence_target: str = ""
    original_claim: str = ""
    contrarian_observation: str = ""
    severity: str = "warn"  # "info" | "warn" | "error"
    resolution: str = "kept_original"
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class Reconciliation:
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    resolutions: list[dict[str, Any]] = field(default_factory=list)
    final_state: str = "all-claims-reconciled"
    def to_dict(self) -> dict[str, Any]: return asdict(self)
```

Allowed `resolution` literals:

- `kept_original` — reserved for info-level matches.
- `downgraded_to_attempted` — optimistic claim weakened to attempted.
- `downgraded_to_unavailable` — environment could not prove the claim.
- `corrected_in_yaml` — YAML rewritten to the observed value.
- `escalated_as_execution_time_required` — downstream executor must verify.

## `final_state` decision tree

`ContrarianValidator.reconcile()` chooses the strongest applicable state:

1. Any `resolution == "escalated_as_execution_time_required"` → `some-claims-escalated-to-execution-time`.
2. Else any `resolution in {"downgraded_to_attempted", "downgraded_to_unavailable"}` → `some-claims-downgraded`.
3. Else → `all-claims-reconciled`.

Never downgrade an `error` to `info`/`warn` merely to make the summary green. The final state must describe what the generator can prove now.

## CLI

`scripts/run_contrarian_validation.py` loads one or more YAML paths, replays `ContrarianValidator` against `validation_evidence.firecrawl.required_maps_present` and `validation_evidence.opensrc.fetched`, prints JSON with per-file `final_state`, and writes `validation_reconciliation` unless `--dry-run` is set.

```bash
# write reconciliation in place
python3 scripts/run_contrarian_validation.py \
  /Users/kiren/.hermes/goal-prompts/<project>-<intent>-tdd-tasks.yaml

# preview only; never writes
python3 scripts/run_contrarian_validation.py --dry-run \
  /Users/kiren/.hermes/goal-prompts/<project>-<intent>-tdd-tasks.yaml

# gate on escalations
python3 scripts/run_contrarian_validation.py --strict \
  /Users/kiren/.hermes/goal-prompts/<project>-<intent>-tdd-tasks.yaml

# multiple YAMLs
python3 scripts/run_contrarian_validation.py --dry-run \
  /Users/kiren/.hermes/goal-prompts/centralize-all-cli-tools-cli-related-tdd-tasks.yaml \
  /Users/kiren/.hermes/goal-prompts/move-my-entire-hermes-setup-tdd-tasks.yaml \
  /Users/kiren/.hermes/goal-prompts/plan-moving-my-entire-hermes-tdd-tasks.yaml
```

There are no `--skill-dir` or `--task-list` flags; YAML paths are positional.

Strict exit codes:

- `all-claims-reconciled` → `0`.
- `some-claims-downgraded` → `0`.
- `some-claims-escalated-to-execution-time` → `2`, and only then.
- Argument or IO errors, including a missing path, → `2`.

`--dry-run --strict` composes: it previews without writing and still returns the strict exit code.

## Canonical failure modes

1. **Firecrawl banner authenticated but live HTTP RST / fetch failed.** `firecrawl --status` can print `Authenticated via FIRECRAWL_API_KEY` before any HTTP request. A later `firecrawl map` / `scrape` may still fail with `ECONNRESET`, `Connection reset`, `fetch failed`, or `Could not fetch` against `api.firecrawl.dev` / `35.245.250.27:443`. Reconcile every dependent row to attempted, unavailable, or execution-time-required. The helper is `research.py::_firecrawl_auth()`.

2. **opensrc cached `main` drift.** Cached source under `~/.opensrc/repos/.../<ref>` may lag upstream. Re-fetch or compare current main/master metadata before trusting line ranges. Reconcile by rewriting paths/SHAs (`corrected_in_yaml`) or downgrading stale citations to attempted.

   Concrete observed mis-citations to NOT repeat from memory (correct each one with `corrected_in_yaml`):

   - **`mastra-ai/mastra` scorers live in `packages/evals/src/scorers`, not `packages/core/src/scorers`.** Citing `packages/core/src/scorers` is a common-sense guess (every other primitive — `agent/`, `workflows/`, `memory/`, `storage/`, `processors/`, `mcp/`, `loop/`, `stream/`, `observability/` — IS under `packages/core/src/`), but Mastra moved scorers under `@mastra/evals` so they share dataset/experiment infra. The contrarian pass catches this immediately. Verify with `ls /Users/kiren/.opensrc/repos/github.com/mastra-ai/mastra/main/packages/core/src/ | grep -i scor` (returns nothing) vs `ls /Users/kiren/.opensrc/repos/github.com/mastra-ai/mastra/main/packages/evals/src/scorers` (returns the directory).

3. **Helper host path absent from remote backend.** A host path such as `/Users/kiren/.hermes/skills/.../scripts/foo.py` can exist locally but be absent inside Daytona, a sandbox, or a remote container. Probe `Path(absolute_path).exists()` inside the backend. Recreate the helper there or escalate to execution-time-required; see `references/remote-backend-helper-unavailable.md`.

4. **YAML principle id declared but unreferenced.** Walk `principles[]` and all task `principle_ids`; every declared id must appear in at least one task. Bind the id to the intended task or delete the dead declaration. Do not mark it `kept_original`.

## Firecrawl 1.16.0 extraction caveat

Firecrawl CLI 1.16.0 top-level commands are `scrape`, `crawl`, `map`, `parse`, `search`, `agent`, `interact`, `experimental`, and `config`; there is no top-level `extract`. Structured extraction routes through `firecrawl agent --schema <json|file> --urls <url[,url...]>`. Reconciliation rule for a literal `firecrawl extract …` evidence row:

- If schema extraction really happened, rewrite it to the equivalent `firecrawl agent --schema-file <path> --urls <url>` and resolve `corrected_in_yaml`.
- Otherwise rewrite to attempted/unavailable/execution-time-required and resolve `downgraded_to_attempted` or `escalated_as_execution_time_required`.

This reference may quote the historical two-word invocation so the rewrite target is clear. The X06 acceptance check forbids that literal only in `src/`, `scripts/`, and `SKILL.md`.

## Validation honesty rule

If a probe cannot run or contradicts an optimistic claim, edit the YAML to say so. Acceptable language: `attempted`, `unavailable`, or `execution_time_required`. A `some-claims-escalated-to-execution-time` final state is valid; silently retaining a false optimistic claim is not.

## `opensrc.fetched[<slug>].key_paths` MUST be real on-disk paths, not descriptive notes

`scripts/run_contrarian_validation.py::_replay_opensrc` walks every entry in `validation_evidence.opensrc.fetched[<slug>].key_paths[]` and calls `Path(kp).exists()` on it. Anything that doesn't resolve on disk is escalated as `opensrc_path_exists` / `escalated_as_execution_time_required` with severity `error`, and the contrarian pass overwrites your existing `validation_reconciliation` block with the union — silently dropping any honest `info` / `warn` reconciliation entries you wrote at generation time.

Symptom (observed in the wild): you write descriptive notes like

```yaml
opensrc:
  fetched:
    live-binary-help-as-source:
      key_paths:
        - "opensrc --help (root: lists fetch, path, list, remove, clean)"
        - "opensrc list --json schema: {updatedAt, packages:[...], repos:[...]}"
```

then run `run_contrarian_validation.py` and get `final_state: some-claims-escalated-to-execution-time` with N error-severity `opensrc_path_exists` conflicts whose `evidence_target` is the slug. Your original 3 generation-time honest reconciliation entries are gone.

Fix: keep `key_paths[]` strictly for paths that exist on disk (the binary, the cache root, the inventory file), and move help-text / schema observations into a sibling field the contrarian pass does not probe. The validator only checks `key_paths`, so a sibling key like `signatures_observed` is safe:

```yaml
opensrc:
  fetched:
    live-binary-help-as-source:
      rationale: "jdx/opensrc not opensrc-fetchable under active GitHub token; authority is the live binary."
      key_paths:                                # contrarian-validated
        - /opt/homebrew/bin/opensrc
        - /Users/kiren/.opensrc/sources.json
        - /Users/kiren/.opensrc/repos
      signatures_observed:                       # not probed; safe for descriptive notes
        - "opensrc --version => opensrc 0.7.2"
        - "opensrc fetch --help => Usage: opensrc fetch [OPTIONS] <PACKAGES>... ; specs: zod, pypi:requests, owner/repo"
        - "opensrc list --json schema: {updatedAt, packages:[...], repos:[...]}"
```

After that change the contrarian pass returns `final_state: all-claims-reconciled` (the new probes pass), at which point you can re-merge your generation-time honest reconciliation entries by writing the `validation_reconciliation` block back yourself with the right severities. The structural validator only enforces `conflicts == resolutions` and the 6 required Conflict fields; it does not require the contrarian pass to be the last writer.

This also applies whenever you want the contrarian pass to attest that the evidence target physically exists. The same rule holds for any future probe that calls `Path(kp).exists()`: cite real paths only, capture descriptions in sibling fields.

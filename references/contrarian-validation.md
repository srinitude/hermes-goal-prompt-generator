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

3. **Helper host path absent from remote backend.** A host path such as `/Users/kiren/.hermes/skills/.../scripts/foo.py` can exist locally but be absent inside Daytona, a sandbox, or a remote container. Probe `Path(absolute_path).exists()` inside the backend. Recreate the helper there or escalate to execution-time-required; see `references/remote-backend-helper-unavailable.md`.

4. **YAML principle id declared but unreferenced.** Walk `principles[]` and all task `principle_ids`; every declared id must appear in at least one task. Bind the id to the intended task or delete the dead declaration. Do not mark it `kept_original`.

## Firecrawl 1.16.0 extraction caveat

Firecrawl CLI 1.16.0 top-level commands are `scrape`, `crawl`, `map`, `parse`, `search`, `agent`, `interact`, `experimental`, and `config`; there is no top-level `extract`. Structured extraction routes through `firecrawl agent --schema <json|file> --urls <url[,url...]>`. Reconciliation rule for a literal `firecrawl extract …` evidence row:

- If schema extraction really happened, rewrite it to the equivalent `firecrawl agent --schema-file <path> --urls <url>` and resolve `corrected_in_yaml`.
- Otherwise rewrite to attempted/unavailable/execution-time-required and resolve `downgraded_to_attempted` or `escalated_as_execution_time_required`.

This reference may quote the historical two-word invocation so the rewrite target is clear. The X06 acceptance check forbids that literal only in `src/`, `scripts/`, and `SKILL.md`.

## Validation honesty rule

If a probe cannot run or contradicts an optimistic claim, edit the YAML to say so. Acceptable language: `attempted`, `unavailable`, or `execution_time_required`. A `some-claims-escalated-to-execution-time` final state is valid; silently retaining a false optimistic claim is not.

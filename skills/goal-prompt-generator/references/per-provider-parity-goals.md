# Per-provider parity goals

Use this when the user asks for a goal whose central job is "make plugin/library X compete with every other plugin/library in the same category Y of project Z" — e.g. "make my Mastra memory plugin perform better on all dimensions than every other Hermes memory provider." The pattern generalizes to any swappable-component category: model providers, terminal backends, vector stores, gateway adapters, scorers, tool-call dispatchers.

## The structural shape

The goal will not write itself from a single prompt. The helper baseline emits ~7 generic tasks; you need ~40+ once parity is taken seriously. Use the `programmatic-yaml-rebuild.md` workflow to construct the YAML from a Python dict.

The phase shape that has worked:

| Phase | Count | Job |
|---|---:|---|
| ANALYSIS | 7–9 | Tool readiness → **inventory every competitor** → audit current plugin → **build the parity matrix** → declare event taxonomy → declare latency budget → declare isolation contract → declare graceful-degradation contract |
| BOOTSTRAP | 4–6 | Test fixtures, parity-matrix harness, perf benchmark harness, lifecycle/recall/observation/end-to-end test scaffolds |
| RED | 1 hard-gate kickoff + ~10 | One failing test per parity dimension. Each test asserts "current plugin equals or beats every competitor on dimension D" |
| GREEN | ~12 | One per RED test, plus aggregator tasks (parity matrix run, observability surface, telemetry) |
| REFACTOR | 5–6 | Styleguide tighten, perf re-bench, parity-matrix lock, validators + contrarian re-run, ruthless final-diff cleanup, sync-and-observe-one-real-session |

## The inventory step is the unlock

Before writing any task, you must materialize the competitor inventory. For Hermes memory the canonical source was `~/.opensrc/repos/github.com/NousResearch/hermes-agent/main/agent/memory_provider.py` (the ABC) plus each `plugins/memory/<name>/__init__.py` (the implementations) plus each `plugin.yaml` (the declared deps + hooks). The inventory must record, per competitor:

- tool schemas exposed (`get_tool_schemas` returns)
- which `MemoryProvider` (or equivalent ABC) hooks the competitor overrides — `initialize`, `prefetch`, `queue_prefetch`, `sync_turn`, `get_tool_schemas`, `handle_tool_call`, `shutdown`, `on_turn_start`, `on_session_end`, `on_session_switch`, `on_pre_compress`, `on_memory_write`, `on_delegation`, plus equivalents for other plugin classes
- prefetch model (sync vs background-thread, blocking vs cached)
- recall mode (semantic, keyword, hybrid, dialectic, peer-card, filesystem-style)
- write surface (server-side extraction, explicit fact tools, hybrid)
- profile-isolation behavior
- credential surface (zero-config vs API-key required)

Cite each finding back to a real opensrc absolute path at a real line range. Skipping this step makes the parity matrix fictional.

## The parity matrix dimensions

Once the inventory exists, cross-join every competitor with every dimension you care about. For a memory plugin the worked set was:

1. cross-session semantic recall recall@K
2. prefetch p50/p99 latency
3. sync_turn write durability
4. keyword search precision
5. cross-session recall hit-rate
6. profile isolation
7. on_pre_compress extraction quality
8. on_session_end summary quality (facts retained / token cost / PII leaked)
9. on_memory_write mirror coverage
10. tool schema count parity (the union of every competitor's surface)
11. graceful degradation under outage
12. credential surface (zero-config vs API-key required)

For each cell, declare `target = max(competitor_score, current_score) + 10%` and persist it to `analysis/parity-matrix.json`. The harness in BOOTSTRAP loads this file; the GREEN aggregator task asserts every cell either PASSES or has a written WAIVER.

## The hard_gate stays mechanical

The RED hard-gate language is the same as the rest of the skill — "no GREEN edits to <file list> have landed since the last BOOTSTRAP commit, AND every R0n test is committed and FAILS for the right reason." For parity goals enumerate the production source files explicitly (`provider.py`, `provider_lifecycle.py`, `server/*`, `tool_schemas.py`, `client.py`, etc.) so future contrarian passes can probe the gate.

## The latency contract block (A05) is mandatory for parity goals

Don't let "make it faster" be implicit. Persist a numeric budget to `analysis/latency-budget.json` with at least: `prefetch_p99_ms`, `sync_turn_p99_ms`, `on_memory_write_p99_ms`, `on_session_end_p99_ms`. The benchmark harness in BOOTSTRAP loads it; the RED task R02 / R11 asserts against it. Without the file, "hot-path zero-blocking-IO" is unenforceable.

## Pitfalls observed

- **Helper baseline has 1–2 RED tasks total.** That is not enough surface to cover 10+ parity dimensions. Always rebuild via programmatic YAML when the goal is parity-shaped.
- **Validator wants `validation_reconciliation.resolutions == validation_reconciliation.conflicts` (literal list equality).** Resolutions cannot diverge in shape or ordering — they must mirror the conflicts list exactly, with one extra `action` key per entry tolerated. Easiest: `resolutions = copy.deepcopy(conflicts)` after you've tagged each conflict with its resolution literal, then write back.
- **Validator requires every declared principle id appears in some task's `principle_ids`.** When the helper emits all 18 P-ids in `principles{}` but the rebuilt phases only reference 15, the validator fails with `principles: unused ids ['P4', 'P15', 'P16']`. Wire the orphans into existing tasks where they fit (P4 → telemetry/circuit-breaker tasks, P15 → caching tasks, P16 → bounded-queue / shared-state tasks) rather than removing them from `principles`.
- **GREEN tasks must reference at least one RED task in `dependencies` directly.** Transitive RED dependency through other GREEN tasks does NOT satisfy the validator. Aggregator GREEN tasks (parity-matrix run, status-surface, telemetry) need explicit `R0n` deps even when they functionally chain through `G00..G08`.
- **Tool-schema parity is the cheapest visible win.** Most categories have a competitor with N tools and your plugin with M < N. Adding the missing tool shapes (profile-style recall, dialectic-style synthesize, filesystem-style browse, explicit-add) is one GREEN task that closes the most-quoted gap users notice.

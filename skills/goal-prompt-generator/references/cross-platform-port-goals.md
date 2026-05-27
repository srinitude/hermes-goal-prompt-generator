# Cross-platform / cross-runtime port goals

When the user asks to **convert / port / rebuild an existing app in framework A (running on runtime A) into a native or first-class app in framework B (running on runtime B)**, the generated goal needs a specific shape that the generic helper baseline does not produce on its own. Examples this reference covers:

- Web (React + three.js / `@react-three/fiber`) → native iOS (Swift 6 + SwiftUI + SceneKit/RealityKit, driven by `getsentry/XcodeBuildMCP`)
- Web (Vue + Babylon.js) → native macOS (Swift + SwiftUI + Metal, MCP-driven)
- React Native → native iOS / native Android with the platform's official MCP toolchain
- Electron desktop → native macOS/Linux/Windows
- Flutter mobile → native iOS+Android
- Vanilla JS Canvas/WebGL app → native (any platform)

The pattern below combines `references/real-implementation-goal-prompts.md` (no scaffolding, real code only), `references/programmatic-yaml-rebuild.md` (Python-dict rebuild + bulk Markdown augmentation), and adds the cross-platform parity-discipline that is the actual contract: the SOURCE folder is the immutable behavior reference, and every primitive / material / light / camera / interaction / screen observed there must have a verified native equivalent.

## When this applies

Trigger keywords / shapes in the user prompt:

- "convert <folder> to native <platform>", "port <X> to <Y>", "rebuild <web app> as a native iOS/macOS/Android app"
- The source is a **built / shipped / production bundle** (Vite/Webpack/Rollup output, `index.html` + minified JS + CSS, `.app`, `.apk`, packaged Electron output) — not raw source you can grep cleanly.
- A specific platform-MCP toolchain is named: `XcodeBuildMCP`, `androidstudio-mcp`, `flutter-mcp`, etc.
- Comprehensive interaction parity is part of the contract (full gesture matrix, every primitive, every material, every screen).
- Vision-based parity verification (screenshots compared against the original) is required.

## Pre-helper inspection probes (always run these first)

Before invoking the helper, probe the source folder so the generated prompt can name the parity targets concretely. This is what turns a generic "convert this folder" prompt into a contract the validator and a downstream coding agent can both consume.

### Step 1 — workdir baseline

```fish
ls -la <source-folder>
file <source-folder>/index.html  # confirm it's a real built bundle
wc -l <source-folder>/index.html
ls -la <source-folder>/assets/   # typical Vite/Rollup output layout
```

### Step 2 — framework fingerprint via ripgrep over the minified bundle

For React + three.js / `@react-three/fiber` web apps the bundle is one big minified JS file, but the original class names of three.js primitives, materials, lights, and cameras survive minification because they're referenced by string in the JSX-compiled code.

```fish
rg -oP '(THREE|R3F|react-three|@react-three|fiber|drei|cannon|use-gesture|framer-motion|gsap|zustand)' <bundle.js> | sort -u
```

This single regex tells you: which 3D library, which React-3D wrapper, which animation/state libraries, and which input library to map. Example output from a real Shapebox conversion run:

```
@react-three
fiber
R3F
react-three
THREE
```

→ React + Three.js + `@react-three/fiber`, no animation library, no state library — clean port.

### Step 3 — enumerate every 3D primitive / material / light / camera

```fish
rg -oP '(BoxGeometry|SphereGeometry|CylinderGeometry|ConeGeometry|TorusGeometry|TorusKnotGeometry|DodecahedronGeometry|IcosahedronGeometry|OctahedronGeometry|TetrahedronGeometry|PlaneGeometry|RingGeometry|CapsuleGeometry|LatheGeometry|TubeGeometry|ExtrudeGeometry|ShapeGeometry|RoundedBoxGeometry|MeshStandardMaterial|MeshPhysicalMaterial|MeshBasicMaterial|MeshToonMaterial|PerspectiveCamera|OrthographicCamera|DirectionalLight|AmbientLight|PointLight|SpotLight|HemisphereLight)' <bundle.js> | sort | uniq -c | sort -rn
```

The output gives you the **exhaustive parity target list** the generated goal must name. Real example:

```
144 Mesh
 52 SpotLight
 51 Group
 37 PointLight
 18 Scene
 16 MeshStandardMaterial
 ...
  3 BoxGeometry, SphereGeometry, CylinderGeometry, ...  (one occurrence per primitive constructor)
```

Note the `3` count for each primitive: it appears in the JSX, in a stringified type name, and in a switch case — but the primitive IS used. Use the FULL set of primitives observed, not the high-frequency ones.

### Step 4 — confirm research tools BEFORE generation

```bash
firecrawl --status
opensrc --version
which <platform-mcp-binary>   # xcodebuild, claude, etc.
python3 ~/.hermes/skills/software-development/goal-prompt-generator/scripts/probe_firecrawl_reachability.py
```

The Firecrawl probe is the only one that distinguishes "banner-authenticated" from "live-map-probe-succeeds-with-918-links". Run it explicitly before generation so `validation_evidence.firecrawl.auth` lands as `authenticated`, not as a downgraded `unavailable` literal.

## Helper invocation: file-fed prompt, not raw stdin

The helper script tokenizes its prompt argument and classifies the domain by keyword density. Two failure modes observed when feeding it the raw prompt directly:

1. **Heredoc with `--json @-`** — the prompt comes through as the single literal token `@-`, giving `domain: uncertain / confidence: low`, a `# Optimized goal Goal` placeholder title, and a missing `## Software Engineering Core Principles` section (the validator skips that section when domain isn't software-development).
2. **Inline argv with a long quoted string** — fish/bash word-split + shell-escape friction frequently corrupts mid-prompt punctuation (em-dashes, backticks, smart quotes).

**Reliable pattern: file-fed prompt via `cat`:**

```fish
# 1. Write the full enhanced prompt to a temp file FIRST
cat > /tmp/<project>_prompt.txt <<'PROMPT'
Convert the existing <Project> source folder at /abs/path (a built React + Three.js / @react-three/fiber web app
shipped as index.html plus assets/index-*.js and assets/index-*.css) into a fully native iOS application written
in Swift 6 targeting iOS 17 and later. Use the getsentry/XcodeBuildMCP toolchain ...
[full prompt body, including the parity target list from step 3, the gesture matrix, the validation requirements]
PROMPT

# 2. Feed the file content as the positional argument
/opt/homebrew/bin/fish -lc 'python3 ~/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py \
  --workdir /abs/path/to/source-folder \
  --json "$(cat /tmp/<project>_prompt.txt)"'
```

The `--workdir` is crucial: it makes `repository_context` snapshot the SOURCE folder, not the cwd. Verify the resulting JSON's `title` is project-shaped (e.g. `Convert existing shapebox source folder`, NOT `Optimized goal`) and the frontmatter shows `domain: "software-development"` with `confidence: "high"` before doing anything else. If the title is generic, regenerate with a more explicit first sentence — the helper's title-extractor reads the first ~80 chars.

## Standard rebuild scope (40+ tasks)

A cross-platform port goal almost always needs a substantive Python-dict YAML rebuild (per `references/programmatic-yaml-rebuild.md`) because the helper baseline is 7 generic tasks. The phase shape that worked end-to-end for Shapebox iOS:

| Phase | Task count | What lives here |
|---|---|---|
| ANALYSIS (A00–A0n) | 6 | Tool readiness, source-bundle inventory (primitives/materials/lights/cameras/screens), Firecrawl map of every doc root (10+ maps with `--limit 5000`), opensrc fetch every OSS dep (`mrdoob/three.js`, `pmndrs/react-three-fiber`, the platform-MCP repo, the source framework's repo), framework mapping table, test manifest |
| BOOTSTRAP (B00–B0n) | 3–4 | Platform-MCP session context, target-platform project skeleton (Xcode/Android Studio/etc.) with strict-mode + minimum-deployment-target wired in, simulator/emulator boot + baseline build, **baseline screenshots of the ORIGINAL app** captured for later vision parity |
| RED (R00–R1n) | 12–14 | Hard-gate kickoff + one suite per: primitives, materials, lights, cameras, hit-test/selection, simple gestures, continuous gestures, composite gestures, accessibility, screen flows, orientation/size-class, persistence, then a full-suite failure-snapshot task |
| GREEN (G01–G1n) | 12–13 | Smallest production code per RED suite in strict dependency order: primitives → materials → lights → cameras → scene host → simple gestures → continuous → composite → accessibility → screens → orientation → persistence → **vision-parity sweep** |
| REFACTOR (X01–X03) | 3 | Ruthless cleanup, full re-validation + rubric replay over ALL 18 principles (this is the principle-coverage catch-all task), README + final response in the required output format |

Total: ~40 tasks. Every GREEN task carries its corresponding RED in `dependencies` (validator-required). The vision-parity sweep is a GREEN task, not a REFACTOR task — discrepancies must block GREEN completion, not be deferred.

## Required shared-block content (don't skip these)

Cross-platform port goals always need these specific shared rules. The generic helper baseline doesn't emit them.

### Guardrails

- `G_<n>_no_production_before_red` — no production code before R00 + all RED committed and failing for the documented reason
- `G_<n>_platform_mcp_preferred` — prefer the platform MCP (XcodeBuildMCP, etc.) over raw shell invocations; record the MCP tool name used in each task's `learnings`
- `G_<n>_claude_cli_contract` — every change traces to a `claude` CLI invocation with the full required flag set
- `G_<n>_no_user_input_non_final` + `G_<n>_final_marker` — runtime continuation contract
- `G_<n>_vision_parity` — every screen flow has a baseline-and-native screenshot pair under `evidence/baseline-screenshots/` and `evidence/native-screenshots/`; discrepancies must be resolved or documented before `completed`
- `G_<n>_no_silent_gesture_drop` — every gesture category in the matrix is implemented or explicitly mapped; silent omission forbidden
- `G_<n>_real_implementations` — no fake nodes, no stubbed gesture responders, no simulated functionality
- `G_<n>_honest_research_evidence` — Firecrawl/opensrc claims must cite real evidence, not cache-only inspection

### CI commands

Mandatory entries:

- Platform build (`xcodebuild -scheme … build`, `./gradlew assembleDebug`, etc.) — prefer the MCP equivalent
- Platform test (full and per-suite filters)
- Simulator/emulator boot + screenshot + install+launch (MCP-preferred)
- `firecrawl --status` + one `firecrawl map --limit 5000 --json --pretty` per doc root → `research/url-maps/<tech>.json`
- `opensrc fetch <org>/<repo> && opensrc path <org>/<repo>` for every OSS dependency
- `git add -A && git commit -m '<PHASE>(<task-id>): …'` for RED and GREEN commit gates

### Doc roots to Firecrawl-map (iOS port example — adapt per platform)

```
https://developer.apple.com/documentation/swiftui
https://developer.apple.com/documentation/scenekit
https://developer.apple.com/documentation/realitykit
https://developer.apple.com/documentation/uikit/uigesturerecognizer
https://developer.apple.com/documentation/combine
https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/
https://github.com/getsentry/XcodeBuildMCP        # platform MCP repo as a doc root
https://threejs.org/docs/                          # source framework
https://r3f.docs.pmnd.rs/                          # source-framework wrapper
https://react.dev/reference/react                  # source runtime
```

10 maps is the floor for a real conversion. Each `firecrawl map --limit 5000 --json --pretty <root>` should land >50 links; if a map returns ≤5 links, climb to a higher doc root (per `references/coding-agent-task-list-yaml.md`'s "Verify each map has real content").

### OSS repos to opensrc-fetch

Always include:
- The source framework's repo (`mrdoob/three.js`, `flutter/flutter`, `electron/electron`, etc.)
- The source-framework wrapper if any (`pmndrs/react-three-fiber`, `pmndrs/drei`, etc.)
- The platform-MCP repo (`getsentry/XcodeBuildMCP`, etc.)
- The source runtime (`facebook/react`, `vuejs/core`, etc.)

## Markdown bulk-augmentation checklist

Per `references/programmatic-yaml-rebuild.md`, do the Markdown augmentation in ONE `mcp_execute_code` pass with a `replace_until_next_heading(text, marker, new_section, level=…)` helper. For cross-platform ports the per-goal sections that always need substantive rewrite:

- `## Goal` — name the source folder absolute path, the source framework chain, and the target framework chain
- `## Original Intent` — the verbatim user request as a blockquote
- `## Assumptions` — the source bundle is authoritative; the toolchain is local; the platform MCP is reachable; UI framework + 3D framework choice with explicit fallback rules
- `## Research and Source Validation Requirements` — name every Firecrawl doc root and every opensrc repo
- `## Scope` — `### In Scope` enumerates EVERY primitive/material/light/camera/gesture from the bundle inventory; `### Out of Scope` excludes backend, multi-platform-variants, App-Store/TestFlight
- `## Execution Plan` → `### Phase 0..3` — Phase-specific concrete actions, not generic placeholders
- `## Acceptance Criteria` — build/launch/test/parity/vision-comparison/contract-honored each as a numbered criterion
- `## Validation Commands` — copy-pasteable shell shapes for build/test/screenshot/Firecrawl/opensrc/validator
- `## Completion Definition` + `## Failure Conditions` + `## Final Output Requirements` — explicit `GOAL_RUNTIME_STATUS: COMPLETE` marker pinned in completion definition; final response shape includes a gesture-support matrix table

The `## Autonomous Execution Requirement`, `## Non-Execution Guardrail`, `## Goal Runtime Continuation Contract` sections MUST be verbatim from `constants.AUTONOMY`, contain the literal `Do not execute this prompt while generating it.`, and the full `constants.GOAL_RUNTIME_CONTINUATION_CONTRACT` paragraph — the substring validator will reject anything paraphrased. Source them by importing the constants in the Python pass:

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.home() / '.hermes/skills/software-development/goal-prompt-generator/src'))
from goal_prompt_generator.constants import AUTONOMY, GOAL_RUNTIME_CONTINUATION_CONTRACT
```

## Honesty rules specific to ports

- **Source folder is authoritative; do not synthesize features the bundle does not have.** If the inventory shows no rotation gesture in the original, mark rotation as `not-in-original` in the gesture matrix and do not implement it just because it's a "common iOS gesture."
- **Vision parity is a real gate, not a checkbox.** The GREEN-phase `vision-parity sweep` task must compare screenshots pair-by-pair and record discrepancies; if a discrepancy is intentional (target-platform has a different navigation idiom, for example), document it explicitly in the README's `Visual parity notes` section before marking the task completed.
- **Don't claim a research tool was used if it wasn't.** Live Firecrawl probe before generation; if Firecrawl is unauthenticated, set `auth: unavailable` and add an explicit `A00`-class readiness task that the downstream coding agent must pass before any other ANALYSIS task.

## Pitfalls

1. **Feeding the helper a thin prompt and letting `domain: uncertain` slip through.** Always check the resulting frontmatter for `domain: "software-development"` + `confidence: "high"` before proceeding. Re-feed a longer, denser prompt if classification was weak.
2. **Forgetting `--workdir` when the helper runs from a different cwd.** `repository_context` ends up snapshotting the cwd (often the Hermes worktree or `$HOME`), not the source folder. Always pass `--workdir <abs-path-to-source-folder>`.
3. **Inventory-by-memory instead of inventory-by-ripgrep.** Don't enumerate primitives from your training data. Run the regex against the actual minified bundle and list what's there. A primitive that survived minification IS used; a primitive that isn't there must not appear in the parity matrix.
4. **Skipping the vision-parity sweep task.** A port without it is a port that builds clean but looks nothing like the original. The sweep is a GREEN task with `G7_vision_parity` guardrail, not a REFACTOR afterthought.
5. **Letting the platform MCP requirement live only in the Markdown.** The YAML's CI commands must reference platform-MCP equivalents (the validator doesn't enforce this, but a downstream agent will reach for raw `xcrun simctl` and break the guardrail). Encode `# PREFER: <MCP tool name>` annotations on every raw-shell CI command.
6. **Building a gesture matrix from "common iOS gestures" instead of from the source bundle's actual gesture surface.** Mismatched matrix → downstream RED tests for gestures the original never had → wasted GREEN effort. The matrix is the intersection of {what the original supports} and {what the platform's gesture system can express}, plus any explicit accessibility alternatives.
7. **Forgetting that `principle_ids` are bare (`P1`..`P18`), not slugged.** The helper emits the bare-id shape; new tasks built from the rebuild script must match. See `references/programmatic-yaml-rebuild.md` pitfall #15 shape A.

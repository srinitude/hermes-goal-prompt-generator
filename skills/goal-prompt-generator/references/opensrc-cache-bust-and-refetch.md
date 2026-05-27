# opensrc cache bust + parallel refetch (deterministic full refresh)

When the user asks to bust / wipe / refresh / rebuild the entire `opensrc` cache (typically before a generation pass that names many open-source repos and the user wants every cited path re-validated against the current `main` / latest tags), use this deterministic 4-step pattern instead of a one-shot `opensrc clean && for x in ...; do opensrc fetch $x; done` loop.

## The 4 steps

1. **Save inventory FIRST** (before `clean`). The cache itself is the source of truth for what to re-fetch:
   ```bash
   opensrc list --json > /tmp/opensrc-inventory-pre-bust.json
   python3 -c "
   import json
   d = json.load(open('/tmp/opensrc-inventory-pre-bust.json'))
   with open('/tmp/opensrc-packages.txt','w') as f:
       for p in d.get('packages', []):
           f.write(f\"{p['name']}@{p['version']}\n\")
   with open('/tmp/opensrc-repos.txt','w') as f:
       for r in d.get('repos', []):
           name = r['name']
           if name.startswith('github.com/'):
               name = name[len('github.com/'):]
           f.write(f'{name}\n')
   print(f'pkgs: {len(d.get(\"packages\",[]))}, repos: {len(d.get(\"repos\",[]))}')
   "
   cat /tmp/opensrc-packages.txt /tmp/opensrc-repos.txt > /tmp/opensrc-refetch-targets.txt
   ```

   Two file-format rules that matter:
   - Packages must round-trip as `name@version` (e.g. `effect@3.21.2`, `@mastra/core@1.32.1`). `opensrc fetch` accepts the same shape it printed.
   - Repos in `opensrc list --json` come back with a `github.com/` prefix in their `name` field. Strip it — `opensrc fetch <org>/<repo>` does NOT want the prefix and silently fetches the wrong thing if you leave it in.

2. **Bust** the cache:
   ```bash
   opensrc clean              # removes packages AND repos; prints "Cleaned N source(s)"
   ```
   `opensrc clean` has flags for partial busts (`--packages`, `--repos`, `--npm`, `--pypi`, `--crates`) — use them when the user only wants part of the cache rebuilt. Default is full wipe.

3. **Parallel refetch** with a per-target wrapper that classifies OK/FAIL:
   ```bash
   cat > /tmp/opensrc-refetch-one.sh << 'EOF'
   #!/usr/bin/env bash
   target="$1"
   out=$(opensrc fetch --quiet "$target" 2>&1)
   rc=$?
   if [ $rc -eq 0 ]; then
     echo "OK   $target"
   else
     echo "FAIL $target :: ${out//$'\n'/ | }"
   fi
   EOF
   chmod +x /tmp/opensrc-refetch-one.sh

   # Run in background so the agent can keep working; -P 6 is safe for a 100mbit+ link.
   xargs -P 6 -I{} /tmp/opensrc-refetch-one.sh "{}" \
     < /tmp/opensrc-refetch-targets.txt 2>&1 | tee /tmp/opensrc-refetch.log
   ```

   The `${out//$'\n'/ | }` newline-flatten is critical: opensrc's failure output is multi-line, and a single-line `FAIL <target> :: ...` lets you `grep '^FAIL '` for the failure list at the end.

4. **Classify and retry failures**:
   ```bash
   grep '^FAIL ' /tmp/opensrc-refetch.log
   ```

   See "Failure classification" below. Retry transient ones; document permanent ones honestly in `validation_evidence.opensrc.divergences[]`.

## Parallelism tuning

`-P 6` worked for 134 sources in ~2 min on a residential ~500mbit link without rate-limit errors. Don't push past `-P 8` against `github.com` — opensrc clones the repo for each fetch and aggressive cloning trips github's secondary rate limits. If you see a wave of `429` or `too many requests` failures, drop to `-P 3` and re-run only the failed targets.

## Failure classification

Two distinct failure modes appeared in a real 134-source bust-and-refetch and they require different responses:

### Transient (retry — succeeds on second pass)

Signature in stderr:
```
fatal: could not open '/Users/<user>/.opensrc/repos/<org>/<repo>/<v>/.git/objects/pack/tmp_pack_XXXXXX' for reading: No such file or directory
fatal: fetch-pack: invalid index-pack output
```

This is a git-pack race when two parallel `opensrc fetch` invocations collide on neighboring objects in the same parent dir tree. A single-target retry always works:
```bash
opensrc fetch --quiet "<failed-target>"
```

### Permanent (registry truth changed — DO NOT retry)

Signature:
```
✗ <pkg>@<ver>: Version "<ver>" not found for "<pkg>". Recent versions: 3.0.1, 3.0.2, ...
```

This means the previously-cached version was **yanked** from npm/PyPI/crates.io between the original fetch and the bust. Real example from a May 2026 bust: `browserbase@1.8.0` — was cached, yanked from npm, only `3.0.1+` now exist. Don't retry. Either:

- Re-pin the spec to a version that still exists in the registry (`browserbase@3.1.1`), and update any YAML `validation_evidence.opensrc.fetched[<repo>].pinned_version` accordingly,
- Or drop the dependency entirely if a sibling package covers the same surface (in the browserbase case, `@browserbasehq/sdk@2.10.0` is the live successor).

Record the yank under `validation_evidence.opensrc.divergences[]` with the literal registry message, not as a generation-time failure.

## When to add new repos to the same parallel job

If the user is busting the cache as part of preparing a fresh generation pass that ALSO names new repos not in the existing inventory (typical for goal-prompt-generator runs), don't run two sequential bust-then-fetch jobs. Stage two parallel xargs jobs against separate target files and separate log files:

```bash
# Job 1: refresh inventory (134 originals)
xargs -P 6 -I{} /tmp/opensrc-refetch-one.sh "{}" < /tmp/opensrc-refetch-targets.txt | tee /tmp/opensrc-refetch.log &
# Job 2: fetch new primitiva-specific repos (23 new)
xargs -P 6 -I{} /tmp/opensrc-refetch-one.sh "{}" < /tmp/opensrc-primitiva-new.txt | tee /tmp/opensrc-primitiva-new.log &
wait
```

Separate logs make the OK/FAIL summary diffable per cohort: a permanent failure in the originals (registry yank) is fundamentally different from a typo in a newly-added repo slug, and merging the logs hides that distinction.

## Verification before claiming success

After both jobs finish:

```bash
opensrc list --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'packages: {len(d.get(\"packages\",[]))}')
print(f'repos:    {len(d.get(\"repos\",[]))}')
"
du -sh ~/.opensrc
```

Expected shape: total count = (originals re-fetched OK) + (new repos OK). If it's lower, some target was silently dropped — re-grep the logs for `FAIL` and the printable summary at the end of each xargs run.

## Pitfalls

1. **Running `opensrc clean` before `opensrc list --json`.** The inventory is gone the moment `clean` finishes. Always save `/tmp/opensrc-inventory-pre-bust.json` first; the cache size (8.5GB → 612MB residual) is the obvious signal that the bust ran, but the package/repo lists are the only way to recover what to re-fetch.
2. **Forgetting that repos in `opensrc list --json` carry a `github.com/` prefix.** `opensrc fetch github.com/jdx/mise` is treated as an org-name `github.com` and a repo-name `jdx/mise` and fails. Strip the prefix before writing the targets file.
3. **Treating "Version X not found" as a transient failure and retrying.** It's a registry yank — every retry will fail identically. Move to "permanent" handling and re-pin or drop.
4. **Letting the parallel xargs job run in foreground when you have other work to do.** It's a 2–15 min job depending on cache size and link speed; run it in `mcp_terminal background=true` with `notify_on_complete=true` and keep working on the goal generation while it runs. The freshly-busted cache state is identical for `opensrc fetch` calls made later by the goal helper — no synchronization barrier needed.
5. **Using `opensrc fetch <name>@<ver>` without quoting `@scope/name@ver`.** The `@`-scoped name has a literal `@` AND the version `@`, and some shells expand `@` in unquoted contexts (especially zsh with extended globbing). Always quote: `opensrc fetch "@mastra/core@1.32.1"`.
6. **Assuming `opensrc fetch` honors the parent shell's `cwd`.** It doesn't matter for cache writes (cache is at `~/.opensrc/`), but `--cwd <dir>` is the way to influence lockfile-version resolution if you want fetches to pick the version your repo's `package.json` / `pyproject.toml` pins. Default behavior fetches the latest published version of bare names like `effect`.
7. **Trying to bust just the top-level cache directory with `rm -rf`.** Don't. `opensrc clean` is the supported entry point and updates the internal `~/.opensrc/sources.json` inventory atomically. A raw `rm -rf` leaves a stale `sources.json` that says repos are cached when they aren't, and `opensrc list` lies until the next `fetch` rebuilds the inventory.

## When NOT to bust the cache

- Goal generation runs cite specific pinned versions; if the cached version matches the pin, the existing cache is fine and the bust is wasted I/O.
- The user only wants one or two repos refreshed: `opensrc remove <slug>` followed by `opensrc fetch <slug>` is much faster than a full cache rebuild.
- The bust is being proposed as a "just-in-case" pre-generation step. The goal-prompt-generator's contrarian validation pass (`run_contrarian_validation.py`) re-checks key-paths-on-disk for every cited claim — a stale cache surfaces as a `Conflict` with severity `error` and resolution `corrected_in_yaml`, which is the right place to handle drift.

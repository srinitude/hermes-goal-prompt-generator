# Shell-escape pitfall when passing a real goal prompt to the helper script

## The problem

`scripts/generate_goal_prompt.py --json "<prompt>"` is documented as the standard
invocation, but real prompts contain `()`, single quotes, double quotes, backslashes,
and embedded multi-line bullets. When the agent invokes this through a terminal
tool that pipes the command through `bash -c` or `fish -lc '...'`, **bash's `eval`
chokes on the unescaped parens** before the Python script ever runs.

Symptom you'll actually see in `mcp_terminal`:

```
/bin/bash: eval: line 8: syntax error near unexpected token `('
/bin/bash: eval: line 8: `  "Prepare every artifact, draft, asset, ...
   for the Warp "Hermes as first-class CLI agent" PR (warpdotdev/warp#10430), ...
```

The shell sees the open paren `(`, and `bash -c '... "...long string..."'` only
quote-protects against single quotes, not against parens nested inside the
quoted argument when the wrapping shell is also fish or bash going through
multiple eval layers.

## The fix that worked end-to-end

Bypass the wrapping shell entirely by calling the helper through `subprocess.run`
with a real argv list (no shell quoting at all):

```python
# In an mcp_execute_code block:
import subprocess, os

prompt = """Prepare every artifact, draft, asset, ...
- bullet 1 (with parens) and "double quotes" and 'singles'
- bullet 2 spanning multiple
  lines with backslashes \\ and other punctuation
"""

env = os.environ.copy()  # keep FIRECRAWL_API_KEY etc.
script = "/Users/kiren/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py"
res = subprocess.run(
    ["python3", script, "--workdir", "/path/to/repo", "--json", prompt],
    capture_output=True, text=True, env=env, timeout=600,
)
print("EXIT:", res.returncode)
print(res.stdout[-2000:])
print(res.stderr[-500:])
```

Why this works:
- `subprocess.run` with a list invokes the binary directly via `execvp`, so the
  prompt argument is passed as a single C-string with zero shell parsing.
- Parens, quotes, backslashes, and multi-line content all pass through verbatim.
- Environment is preserved explicitly via `env=env`, so `FIRECRAWL_API_KEY` and
  any other helper-required env vars are still available to the child Python.

## When you must stay in the terminal tool

If you need to drive the helper from a fish/bash one-liner (e.g. inside a CI
script), write the prompt to a tempfile and read it via `--input-file`, or pipe
it via stdin from a heredoc:

```bash
cat > /tmp/goal.txt <<'EOF'
Prepare every artifact, draft, asset, ...
- bullets with (parens) and "quotes"
EOF

python3 ~/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py \
  --workdir /path/to/repo \
  --json \
  "$(cat /tmp/goal.txt)"
```

The `'EOF'` form (single-quoted) prevents bash from expanding `$VAR` inside the
prompt; use unquoted `EOF` only when you actually want variable expansion.

## Pitfalls of the wrong workarounds

1. **Re-quoting the prompt with `\"` escapes.** Counting nested quotes by hand
   for a 50+ line prompt is impractical and breaks under the slightest copy-paste
   edit. Use `subprocess.run` with a list, not escape gymnastics.
2. **Stripping parens / quotes from the prompt.** The whole point is that the
   user's goal text is free-form prose. Mutating it to satisfy the shell loses
   information that the generator depends on (acceptance criteria phrasing,
   issue references like `repo#10430`, code-style hints).
3. **Using `--input-file` with a `.md` file the user already created.** This
   path triggers helper *regeneration* of an existing valid file, not first-pass
   generation from raw text. See `references/revalidating-existing-files.md` for
   the in-place-validation alternative.

## Trigger heuristic

If you write `terminal(... "$prompt" ...)` and the prompt is more than ~3 lines
or contains any of `()` `'"` `\` `*` `<` `>`, **don't bother trying to shell-quote
it.** Reach straight for `mcp_execute_code` + `subprocess.run([...])`.

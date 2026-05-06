# Research Tool Readiness During Goal Prompt Editing

When a generated goal prompt requires a specific research or validation tool (for example Firecrawl `map --limit 5000`, `opensrc`, or provider docs scraping), distinguish **prompt-generation evidence** from **future goal-execution requirements**.

## Pattern

1. Probe the requested tool before saying it was used.
   - Firecrawl example: `FIRECRAWL_NO_TELEMETRY=1 firecrawl --status`.
   - If mapping is required, run a small/auth-checking map command or verify credentials are available.
   - Firecrawl CLI may exit `0` while printing an auth/setup prompt such as "Welcome! To get started, authenticate..." instead of map JSON. Treat that as **not usable** for source validation and do not claim mapping succeeded.
2. If the tool is usable, record the mapped source requirement normally in the generated prompt.
3. If the tool is unavailable or unauthenticated, keep the tool requirement in the prompt as an execution-time validation requirement, but do not label alternate discovery as tool-validated.
4. If you use another lookup mechanism to seed targets, label it honestly, e.g. `initial_discovery_evidence: "web_search result; validate with Firecrawl map: ..."`.
5. If the user directly supplies an additional target URL, add it without inventing discovery evidence and label it as user-provided, e.g. `initial_discovery_evidence: "user-provided target; validate with Firecrawl map: <name> documentation at <url>"`.
6. When an existing valid generated prompt contains duplicated preserved original-intent sections, apply list additions and requirement edits to every semantically duplicated location, then validate once in place.
7. Avoid broad `replace_all` patches anchored only on generic Markdown delimiters such as ``` or `---`; they can insert the same requirement after every code fence. Patch around unique headings or surrounding sentences, then search for the inserted phrase and remove duplicates before validation.
8. Run the in-place validator after edits to ensure the generated Markdown contract still passes.

## Pitfall Example

Bad phrasing when Firecrawl is unauthenticated:

```yaml
official_source_evidence: "Firecrawl search result: Claude Code overview"
```

Better phrasing:

```yaml
initial_discovery_evidence: "web_search result; validate with Firecrawl map: Claude Code overview"
```

User-provided target phrasing:

```yaml
initial_discovery_evidence: "user-provided target; validate with Firecrawl map: Pi documentation at https://pi.dev"
```

This preserves the user's requested Firecrawl requirement without falsely claiming Firecrawl was available during prompt editing.

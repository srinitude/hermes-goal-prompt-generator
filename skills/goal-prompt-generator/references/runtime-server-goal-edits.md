# Runtime/Server Requirements in Generated Goal Prompts

Use this when editing an existing generated goal prompt to add a concrete runtime/server contract (for example Mastra on Bun with Hono) without executing the goal.

## Workflow

1. Treat the request as an in-place prompt edit when the target is an existing valid generated `.md` goal file.
2. Inspect likely duplicated sections: top-level invocation instruction, preserved original intent, documentation validation, per-project/server contract, schema, tests, final outputs, and final acceptance.
3. Patch every semantic duplicate intentionally. Avoid generic anchors such as code fences or `---` separators.
4. Add the runtime/server requirement in all of these places when applicable:
   - top-level additional invocation instruction;
   - documentation validation source list;
   - explicit contract section before implementation deliverables;
   - generated scaffold/file tree;
   - project config/runtime schema;
   - init/server preflight steps;
   - forbidden/allowed wrapper rules;
   - tests and final acceptance criteria;
   - research artifacts for URL maps, knowledge, and claim verdicts.
5. Probe requested tools before saying validation was performed. If Firecrawl is unauthenticated, preserve the Firecrawl requirement as execution-time validation and label alternate evidence honestly.
6. For source validation, `opensrc path https://github.com/<owner>/<repo>` works with opensrc 0.7.x and resolves to a cached tree under `~/.opensrc/repos/github.com/<owner>/<repo>/main`.
7. Run the in-place validator after edits.
8. Search inserted phrases and counts to confirm duplicated sections are balanced.

## Example: Mastra on Bun + Hono

For a Mastra project server that must run on Bun with Hono, require:

- Bun is the normal runtime/package runner/server runtime.
- Hono is the HTTP server framework.
- `@mastra/hono` binds a typed `Hono` app to the project `Mastra` instance.
- The Hono app is served by Bun-native APIs such as `Bun.serve({ fetch: app.fetch, ... })` or the documented Hono-on-Bun equivalent.
- Node-only runtime server paths such as Express/Fastify/Koa/Next API routes/`@hono/node-server` are forbidden for the generated project server unless recorded as upstream-doc comparison only.
- Hono route boundaries validate schemas and propagate RequestContext/current-agent model/cancellation/evidence/project/work IDs into Mastra workflows.

Useful validation targets:

- Firecrawl maps: `https://mastra.ai/docs`, `https://mastra.ai/reference`, `https://mastra.ai/guides`, `https://mastra.ai/models`, `https://bun.com/docs`, `https://hono.dev/docs/`.
- opensrc: `https://github.com/mastra-ai/mastra`, `https://github.com/oven-sh/bun`, `https://github.com/honojs/hono`.

Source-grounded facts observed in one session:

- Mastra source includes docs/reference for a Hono adapter under its repo, including `@mastra/hono`, `MastraServer({ app, mastra })`, and `await server.init()`.
- Hono source/docs state Hono works across runtimes including Bun and exports Bun adapter helpers such as `hono/bun` WebSocket support.
- Bun source/docs include runtime/server references that can ground Bun-native serving requirements.

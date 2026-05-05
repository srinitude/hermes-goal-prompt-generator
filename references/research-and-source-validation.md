# Research and Source Validation Notes

This skill was originally created after validating Hermes Agent documentation and source behavior. The current refactor narrows the package to isolated prompt generation only.

## Documentation and source checked

- Hermes Agent documentation was mapped with Firecrawl.
- Goal docs, skills docs, plugin docs, hooks docs, CLI command docs, and slash command docs were inspected.
- Hermes source was inspected with `opensrc path NousResearch/hermes-agent`.

## Current conclusion

Hermes Agent's built-in `/goal` command is a separate execution workflow. `goal-prompt-generator` should not hook into it automatically.

The generator now focuses on:

- generating one Markdown prompt file from one raw goal prompt,
- validating metadata and required sections,
- preserving traceability through `source_prompt_hash`,
- enforcing non-execution during generation,
- saving output in the explicit execution directory.

No source-level Hermes `/goal` patch is part of this repository after the isolation refactor.

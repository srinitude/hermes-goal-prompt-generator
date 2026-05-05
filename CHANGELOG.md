# Changelog

## 1.0.1 - Isolated generation refactor

- Refocuses `goal-prompt-generator` on explicit, isolated Markdown goal prompt generation.
- Removes packaged Hermes `/goal` preflight/source-integration patch content.
- Adds an isolated generation boundary section to generated Markdown.
- Updates validation to reject generated files that lack the isolation boundary.
- Clarifies that Hermes Agent's built-in `/goal` command is not intercepted or modified.

## 1.0.0 - Initial release

- Added Hermes Agent skill content, linked references/templates/scripts, standalone Python package, CLI, tests, examples, and CI workflow.

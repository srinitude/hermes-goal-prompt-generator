# Security Policy

`goal-prompt-generator` is deterministic and should not require credentials, API keys, or network access.

## Reporting issues

Please open a GitHub issue for security-sensitive behavior such as:

- executing or partially executing the generated goal during optimization;
- writing outside the requested execution directory;
- failing to regenerate incomplete optimized files;
- leaking secrets through generated output.

## Secret handling

Do not include real credentials, tokens, connection strings, or private `.env` files in prompts, examples, tests, issues, or generated fixtures.

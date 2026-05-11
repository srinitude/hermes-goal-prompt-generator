# Installation

## Install as a Hermes skill

```bash
git clone https://github.com/srinitude/hermes-goal-prompt-generator.git
cd hermes-goal-prompt-generator
mkdir -p ~/.hermes/skills/software-development
ln -sfn "$(pwd)" ~/.hermes/skills/software-development/goal-prompt-generator
hermes skills list | grep goal-prompt-generator
```

Restart Hermes or run `/reset` so the skill loader refreshes.

This installs an explicit-use skill. It does not modify Hermes Agent's built-in `/goal` command.

## Install standalone CLI for local development

```bash
uv sync --extra dev
uv run goal-prompt-generator --help
```

## Verify

```bash
mise run quality
```

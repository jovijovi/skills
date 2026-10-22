# Agent Skills

Free for all humans!

Each skill is a folder with a `SKILL.md` file in the [Agent Skills](https://agentskills.io/specification) format. Any agent that supports the format can use it.

## Skills

| Skill | What it does |
|---|---|
| [decide-with-me](skills/decide-with-me/SKILL.md) | Discuss open choices through short rounds of multiple-choice questions, then confirm a plan before acting. |
| [openai-gpt-image-api](skills/openai-gpt-image-api/SKILL.md) | Generate and edit images with OpenAI GPT Image models through the Image API. |
| [xiaohongshu-extract](skills/xiaohongshu-extract/SKILL.md) | Extract note metadata from public Xiaohongshu links. |

## Install

Link or copy a skill folder into a directory that your agent scans:

| Agent | User-level skills directory |
|---|---|
| Codex, Cursor, OpenCode, Pi, Oh My Pi, Kimi Code CLI | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| Hermes Agent | `~/.hermes/skills/`, or add `~/.agents/skills` to `skills.external_dirs` in `~/.hermes/config.yaml` |

For example, with symbolic links so that `git pull` also updates the installed skills:

```bash
git clone https://github.com/jovijovi/skills.git
mkdir -p ~/.agents/skills ~/.claude/skills
ln -s "$PWD/skills/skills/decide-with-me" ~/.agents/skills/decide-with-me
ln -s ../../.agents/skills/decide-with-me ~/.claude/skills/decide-with-me
```

Start a new agent session after installing. OpenCode and Cursor also read `~/.claude/skills/`, so a skill linked into both directories can appear twice there.

## License

MIT License

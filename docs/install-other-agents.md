# Install the VAKYN skills in Codex, Cursor and OpenCode

The skills follow the [Agent Skills](https://agentskills.io) format, so any agent that reads
`SKILL.md` folders can use them. The [`skills`](https://github.com/vercel-labs/skills) installer
copies them in with one command. You need Node.js 22.20 or newer for `npx`.

## Install

From your project folder:

```bash
npx skills add vakyn-ai/skills --skill '*' -a codex -a cursor -a opencode
```

Install all the skills (`--skill '*'`). They link to each other's reference pages, and those links
only resolve when the skills sit side by side.

Where they land:

| Agent | This project | All projects (`-g`) |
|---|---|---|
| Codex | `.agents/skills/` | `~/.agents/skills/` |
| Cursor | `.agents/skills/` | `~/.agents/skills/` |
| OpenCode | `.agents/skills/` | `~/.agents/skills/` |
| Claude Code (`-a claude-code`) | `.claude/skills/`, linked to `.agents/skills/` | `~/.claude/skills/` |

The three agents share one copy in `.agents/skills/`. Commit that folder and `skills-lock.json`
to give your team the same skills.

Options:

- `-g`: install once for every project instead of this one.
- `-y`: skip the questions (scope, copy or link).
- `--copy`: copy files instead of linking them, for systems without symlinks.
- Leave out the `-a` flags to pick from the agents the installer finds on your machine.

Start a new session afterwards. Check that the agent sees them:

- Codex: type `/skills`, or name one in a prompt with `$vakyn`.
- Cursor: ask the agent which skills it has.
- OpenCode: run `opencode debug skill`.

Claude Code users: the plugin in the [README](../README.md#install-30-seconds) is the better route.
It updates itself.

## Update

```bash
npx skills update -p -y      # skills installed in this project
npx skills update -g -y      # skills installed with -g
```

`update` compares each skill with the repository and reinstalls the ones that changed. Skills
installed from a local folder are not tracked; run `add` again to refresh them.

## Remove

```bash
npx skills remove --all              # every skill in this project, from every agent
npx skills remove check -y     # one skill
npx skills remove -g --all           # skills installed with -g
```

## If the clone fails

`npx skills add` clones with your normal Git sign-in. If HTTPS asks for a password and fails,
use the SSH address:

```bash
npx skills add git@github.com:vakyn-ai/skills.git --skill '*' -a codex -a cursor -a opencode
```

To try a branch, add `#<branch>` to the address.

## Without the installer

Copy the folders yourself. Keep them side by side:

```bash
git clone --depth 1 https://github.com/vakyn-ai/skills /tmp/vakyn-skills
mkdir -p .agents/skills && cp -r /tmp/vakyn-skills/skills/* .agents/skills/
```

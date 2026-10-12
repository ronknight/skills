# Agent skills

Practical skills for coding agents (Claude Code, Codex, Cursor, Copilot and
other tools that read `SKILL.md`). Each one comes from a failure that happened
in real work, written up so an agent avoids it.

| Skill | What it does |
|---|---|
| [`definition-of-done`](skills/definition-of-done/SKILL.md) | Keeps docs in step with code on every change: snapshot, changelog, docs, diagrams, ADRs, and an explicit report of skipped steps. Includes snapshot scripts for Bash and PowerShell. |
| [`ai-safety-guardrails`](skills/ai-safety-guardrails/SKILL.md) | Approval gates, dry-runs, recoverability checks and production separation for destructive or outward-facing actions. Includes an `AGENTS.md` section template. |
| [`excel-com-safe-write`](skills/excel-com-safe-write/SKILL.md) | Excel COM writes that can't silently vanish: guard, back up, write, verify. Includes a PowerShell script. |
| [`html-email-jinja`](skills/html-email-jinja/SKILL.md) | HTML marketing emails from Jinja templates that survive Gmail, Outlook and dark mode. Includes a starter skeleton and a stdlib-only linter. |
| [`api-audit`](skills/api-audit/SKILL.md) | Audits a poorly documented vendor API safely: test environment first, field-by-field write probes that catch silently ignored updates, redacted logs, a report and a vendor ticket. Includes a Postman inventory script that flags embedded credentials. |

## Install

```bash
npx skills add ronknight/skills
```

To install by hand, copy a folder from `skills/` into your agent's skills
directory, for example `~/.claude/skills/<name>/` for Claude Code.

## Layout

```
skills/<name>/
  SKILL.md        # frontmatter (name, description, license) + instructions
  scripts/        # optional helpers the skill calls
  references/     # optional templates loaded on demand
```

## Contributing

Issues and pull requests are welcome. Keep skills generic: no company names,
internal paths, credentials, or vendor details that aren't public.

## License

[MIT](LICENSE)

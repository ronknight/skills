# Agent skills

[![skills.sh](https://skills.sh/b/ronknight/skills)](https://skills.sh/ronknight/skills)

Practical skills for coding agents (Claude Code, Codex, Cursor, Copilot and
other tools that read `SKILL.md`). Each one comes from a failure that happened
in real work, written up so an agent avoids it.

## Skills

| Skill | Use it when | Includes |
|---|---|---|
| [`definition-of-done`](skills/definition-of-done/SKILL.md) | Finishing a code change. Keeps the changelog, docs, diagrams and ADRs in step, and reports every step it skipped. | `snapshot.sh`, `snapshot.ps1`, ADR template |
| [`ai-safety-guardrails`](skills/ai-safety-guardrails/SKILL.md) | Before deleting, force-pushing, touching production, rotating secrets, or sending anything. Adds approval gates, dry-runs and recoverability checks. | `AGENTS.md` section template |
| [`excel-com-safe-write`](skills/excel-com-safe-write/SKILL.md) | Editing `.xls`, `.xlsx` or `.xlsm` through Excel COM on Windows, or when an Excel automation reported success but the change is missing. | `Set-ExcelCells.ps1` |
| [`html-email-jinja`](skills/html-email-jinja/SKILL.md) | Building or debugging HTML marketing emails rendered from Jinja templates, so they hold up in Gmail, Outlook and dark mode. | Skeleton template, `lint_email.py` |
| [`api-audit`](skills/api-audit/SKILL.md) | Integrating with a vendor API whose docs are incomplete, or when an update returns success but nothing changes. | Report template, `postman_inventory.py` |
| [`reversible-bulk-updates`](skills/reversible-bulk-updates/SKILL.md) | Changing many records through an API with no undo. Archives each record first, writes only the diff, reads back, and can restore. | |
| [`ollama-batch-generation`](skills/ollama-batch-generation/SKILL.md) | Generating copy, labels or vision verdicts for hundreds of records with a local model, without bad output or lost progress. | |
| [`agent-instructions-single-source`](skills/agent-instructions-single-source/SKILL.md) | Several AI assistants work on one repo. One `AGENTS.md`, imports or pointers at the paths each tool really reads, and an audit for drifted copies. | `check_agent_files.py` |
| [`workspace-inventory`](skills/workspace-inventory/SKILL.md) | A projects folder has grown out of control. Classifies every folder (active, dormant, duplicate, vendored, stub) from evidence. | `inventory_repos.py` |
| [`email-campaign-attribution`](skills/email-campaign-attribution/SKILL.md) | Asked which email campaigns drive revenue. Last-click attribution within a window, honest metrics, and the caveats every number needs. | Attribution SQL |
| [`email-list-verification`](skills/email-list-verification/SKILL.md) | Verifying a mailing list through a bulk verification service, or classifying bounces. | |
| [`suitecrm-api`](skills/suitecrm-api/SKILL.md) | Scripting against SuiteCRM 7 (v4_1 REST or V8), searching by email, or merging duplicate accounts. | |
| [`legacy-xls-python`](skills/legacy-xls-python/SKILL.md) | An importer needs real Excel 97-2003 `.xls`, or a "spreadsheet" won't open. Detects what the file really is and picks the right library. | `sniff_spreadsheet.py` |
| [`print-tiff-to-web-images`](skills/print-tiff-to-web-images/SKILL.md) | Converting print TIFF product photos for the web: colours, transparency without holes, sizes, and checking published URLs. | |

## Install

Install every skill with the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add ronknight/skills
```

Choose what to install:

```bash
npx skills add ronknight/skills --list                  # show the skills without installing
npx skills add ronknight/skills --skill api-audit       # one skill (repeat --skill for more)
npx skills add ronknight/skills -a claude-code -g       # one agent, for your user rather than this project
```

To install by hand, copy a folder from `skills/` into your agent's skills
directory, for example `~/.claude/skills/<name>/` for Claude Code.

## Requirements

The skills are Markdown and work in any agent that reads `SKILL.md`. Only the
bundled scripts have requirements:

| Script | Needs |
|---|---|
| `snapshot.sh` | Bash and `tar` (macOS, Linux, Git Bash); `git` optional |
| `snapshot.ps1` | Windows PowerShell 5.1 or PowerShell 7 on Windows; `git` optional |
| `Set-ExcelCells.ps1` | Windows with Microsoft Excel installed |
| `lint_email.py`, `postman_inventory.py`, `check_agent_files.py`, `sniff_spreadsheet.py` | Python 3.8 or later, standard library only |
| `inventory_repos.py` | Python 3.8 or later, standard library only; `git` on the PATH |

## Security

- The scripts install nothing, download nothing and make no network calls.
- No script prints a credential. `postman_inventory.py` reports where a secret
  sits in a collection, never its value.
- Skills that touch outside systems (vendor APIs, email platforms, production)
  tell the agent to use a test environment first, read credentials from
  environment variables, treat fetched content as data rather than
  instructions, and ask before anything destructive or outward-facing.
- skills.sh audits every skill with Gen Agent Trust Hub, Socket, Snyk, Runlayer
  and ZeroLeaks. The results are on each skill's page under **Security**.

[SECURITY.md](SECURITY.md) lists what each script reads, writes and connects
to, and how to report a vulnerability.

## Layout

```
skills/<name>/
  SKILL.md        # frontmatter (name, description, license) + instructions
  scripts/        # optional helpers the skill calls
  references/     # optional templates loaded on demand
scripts/          # repo maintenance; not installed with any skill
```

## Contributing

Issues and pull requests are welcome. A skill should:

- come from a failure that really happened, written up as general practice: no
  company names, internal paths, credentials, or vendor details that aren't
  public;
- have a `name` (lowercase, hyphens) and a `description` that says what it does
  and when to use it;
- keep its scripts dependency-free and offline, and make anything destructive
  refuse by default or offer a dry run.

## Maintaining

| Command | What it checks |
|---|---|
| `scripts/check-private-terms.sh` | Fails if any file git would publish contains a term from the local, git-ignored `.private-terms.txt`, an e-mail address, or a user-profile path. Run it before every commit. |
| `python scripts/check_audits.py` | Prints the skills.sh audit results for every skill and exits 1 on a fail (`--strict` also fails on a warn). Results appear a few minutes after the first `npx skills add` with telemetry on. |

## License

[MIT](LICENSE)

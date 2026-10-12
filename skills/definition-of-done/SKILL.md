---
name: definition-of-done
description: Keep docs in step with code on every change - restore-point snapshot before risky edits, a dated CHANGELOG entry, updated docs, refreshed mermaid diagrams when flow changes, and an ADR for architectural decisions, ending with a one-line report per artifact and explicit skips. Use after finishing a code change, before committing, when asked whether the docs are up to date, or when a repo's AGENTS.md/CLAUDE.md asks for a Definition of Done.
license: MIT
---

# Definition of Done

Documentation is part of the change, not a later phase. Do these steps as you
finish a change. You don't need permission to do them, but you must say what
you did.

## 0. Learn the repo's conventions first

Look at what exists before writing anything:

- `CHANGELOG.md`: follow its format. If there isn't one, ask before creating it.
- `docs/`: which files describe the area you touched?
- Diagrams: mermaid files in `docs/`, `openspec/diagram/`, `architecture/` or similar.
- ADRs: `docs/adr/`, `docs/decisions/`, `adr/`. Reuse the repo's template if it
  has one, otherwise use [references/adr-template.md](references/adr-template.md).
- Repo instructions (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`) win over this skill.

Don't introduce structure the repo doesn't use (a `docs/` tree, an ADR folder)
without asking.

## 1. Restore point, before a risky change

Before a large refactor, a dependency upgrade, a bulk config edit, or anything
hard to undo, snapshot the project:

```bash
scripts/snapshot.sh [project_dir]              # macOS, Linux, Git Bash
```
```powershell
scripts\snapshot.ps1 [-ProjectPath <dir>]      # Windows PowerShell
```

Both copy the project to `archive/<YYYY-MM-DD_HHmmss>/`. They skip `.git`,
virtualenvs, `node_modules` and caches at any depth, plus top-level `archive`,
`build`, `dist` and `target`. They refuse to run if `archive/` is not
git-ignored.

- The snapshot includes ignored files such as `.env`. That is why `archive/`
  must be git-ignored. Otherwise, pass an archive folder outside the repo.
  Never commit, upload or share a snapshot.
- It sits on the same disk. It is a quick rollback, not a backup.
- If the working tree is clean and the change will be committed, git is already
  the restore point. Snapshot when there is uncommitted work, or ignored and
  untracked files (local config, data, databases) that git can't bring back.

## 2. Changelog

Read the diff first: `git status --short`, `git diff --stat`, `git diff`. You
can't describe a change you haven't read.

Add an entry under `## [Unreleased]` in the right Keep a Changelog group
(`Added`, `Changed`, `Fixed`, `Removed`), dated with today's real date:

```markdown
### Changed
#### 2026-10-12 - Retry webhook delivery with backoff
A single timeout used to drop the event for good, so short outages lost data.

- **`src/webhooks/sender.py`** - retries timeouts and 5xx responses up to 5 times with exponential backoff.
- **`config/*.yaml`** (4 files) - new `webhook_retry` block; defaults keep the old behaviour.
```

Lead with why, then name the files. Collapse bulk edits into one bullet with a
count. A line written only to satisfy a hook is worse than no line.

## 3. Docs

Update every doc the change made false:

- README usage when CLI flags, env vars, config shape or install steps change.
- Guides and runbooks for the area you touched.
- API docs when a request or response shape changes.
- Specs that the change contradicts. A stale spec misleads the next reader.

Put new documentation where the repo keeps it, not as loose markdown at the root.

## 4. Diagrams

If data flow, control flow, or the user's path through the product changed,
update the matching mermaid diagram. Edit the nodes that changed and keep the
existing style rather than regenerating the whole graph. Check it still parses:
balanced brackets, and quotes around labels that contain `()`, `[]`, `:` or `/`.

## 5. ADR, for architectural decisions only

Write one for a new dependency or service, a changed data contract or storage
format, or a structural choice that had real alternatives. Skip it for routine
fixes.

File it as `docs/adr/YYYYMMDD-<kebab-title>.md` (or the repo's own pattern).
Record the alternatives you rejected and why. An ADR that names only the winner
is just a changelog entry.

## 6. Report

End with one line per artifact you touched, and name every step you skipped
with the reason:

```
Docs: CHANGELOG (Unreleased > Changed), docs/webhooks.md (retry section), dataflow diagram (retry loop).
Skipped: ADR (no architectural decision), snapshot (clean tree, change is committed).
```

This skill exists to stop steps being dropped silently.

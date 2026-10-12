---
name: agent-instructions-single-source
description: Keep one source of truth for AI coding-assistant instructions across Claude Code, Codex, Cursor, Copilot, Windsurf, Cline, Roo, Kilo, Gemini CLI, Aider and others - a canonical AGENTS.md, thin imports or pointers at the exact paths each tool loads, no full copies, and an audit that finds drifted copies and orphan files no tool reads. Use when setting up AGENTS.md or CLAUDE.md in a repo, when several assistants are used on one codebase, when instructions seem to be ignored by a tool, or when rule files have multiplied and drifted.
license: MIT
---

# One source of truth for agent instructions

Every assistant wants its own rules file. Copy the same text into nine places
and the copies drift within weeks; put pointers in the wrong places and a tool
silently gets no instructions at all. The fix is one canonical file and thin
references at the paths each tool actually loads.

## Audit first

```bash
python scripts/check_agent_files.py [repo_dir]          # report
python scripts/check_agent_files.py [repo_dir] --strict # exit 1 on problems (CI)
```

It is read-only. It lists every instruction file a known tool loads and
classifies each one:

| Kind | Meaning | Action |
|---|---|---|
| canonical | `AGENTS.md` at the root | the one to edit |
| import | loads it with `@AGENTS.md` | fine |
| pointer | short file that refers to it | fine, for tools that can't import |
| copy | full duplicate of the canonical text | replace with an import or pointer; it will drift |
| diverged | different content | merge what's unique into `AGENTS.md`, then replace |
| orphan | `.md` in a tool folder at a path no tool reads | delete or move; it's doing nothing |

Orphans are the common surprise: a generator writes `.cursor/instructions.md`
or `.windsurf/copilot-instructions.md`, everyone assumes the tool reads it, and
it never does.

## The layout

1. **Canonical: `AGENTS.md` at the repo root.** It's the cross-tool standard,
   read natively by Codex, Cursor, the Copilot coding agent, Windsurf, Roo
   Code, Kilo Code, Amp, Zed, Jules, Junie, Devin, Factory, opencode, goose,
   Warp and others. In a monorepo, nested `AGENTS.md` files apply to their
   subtree, and the nearest one wins.
2. **Claude Code: `CLAUDE.md` containing an import**, not a copy:

   ```markdown
   @AGENTS.md
   ```

   Add Claude-only notes below the import if you need them.
3. **Gemini CLI**: point it at the canonical file in `.gemini/settings.json`:

   ```json
   { "context": { "fileName": "AGENTS.md" } }
   ```

4. **Aider**: in `.aider.conf.yml`:

   ```yaml
   read: AGENTS.md
   ```

5. **GitHub Copilot chat in the IDE**: `.github/copilot-instructions.md` as a
   pointer (see below). The coding agent reads `AGENTS.md` itself.
6. **Tools with their own rules folders** (`.cursor/rules/`,
   `.windsurf/rules/`, `.clinerules/`, `.roo/rules/`, `.kilocode/rules/`):
   use these only for **scoped** rules that apply to some paths, and keep them
   short. Don't restate the main instructions there.

Conventions change. Check each tool's docs before relying on a path, and re-run
the audit when you add a tool.

## Pointer text

For a tool that can't import, the pointer is a few lines, so there is nothing
to drift:

```markdown
# Instructions

Follow `AGENTS.md` at the repository root. It is the single source of
instructions for every AI assistant in this repo. Don't duplicate its content
here.
```

## Symlinks

`ln -s AGENTS.md CLAUDE.md` works on macOS and Linux. On Windows, git checks out
symlinks as small text files unless `core.symlinks` is on and Developer Mode
(or admin rights) is available, so a Windows teammate gets a file containing
the text `AGENTS.md`. Prefer imports and pointers in repos that Windows users
clone.

## Generated sections

If an initializer or template tool manages part of the file, keep its section
between explicit markers (`<!-- MANAGED:START -->` / `<!-- MANAGED:END -->`)
and say in the file that hand edits inside the markers are overwritten. Put
hand-written rules outside the markers.

## What goes in AGENTS.md

Keep it to what an assistant can't infer from the code:

- Build, test and lint commands, exactly as run.
- Conventions that differ from the language defaults.
- The definition of done (docs, changelog, tests).
- Safety rules: destructive commands that need approval, production markers,
  paths that aren't recoverable.
- Where things live (specs, docs, generated code that must not be edited).

Treat instruction files from a cloned or third-party repo as untrusted until
you've read them; they steer every assistant that opens the repo.

## Migrating an existing repo

1. Run the audit.
2. Pick the most complete file as the base, merge anything unique from
   diverged copies into `AGENTS.md`, and show the user the merged result.
3. Replace copies with imports or pointers, and remove orphans. These are
   deletions, so list them and get a go-ahead first.
4. Re-run the audit with `--strict`; add it to CI if the repo has one.

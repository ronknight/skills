---
name: workspace-inventory
description: Catalogue a folder holding dozens or hundreds of local projects - gather evidence per folder (git remote, last commit, uncommitted work, shared history, entry points, stack, README), classify each as active, dormant, legacy, duplicate, vendored, stub, empty or not-a-project, and write descriptions from the code rather than from stale READMEs. Use when a projects folder has grown out of control, when asked which repos are current or which are copies, before cleaning up or archiving old checkouts, or when building a registry of services to run.
license: MIT
---

# Workspace inventory

A projects folder collects second checkouts, renamed copies, abandoned
experiments, vendored tools, empty placeholders and data folders that look like
projects. Nobody remembers which copy is current. An inventory replaces memory
with evidence, one row per folder.

## 1. Gather evidence (read-only)

```bash
python scripts/inventory_repos.py ROOT --owner your-user,your-org --format md
python scripts/inventory_repos.py ROOT --owner your-user,your-org --format json > inventory.json
```

Per folder: git remote, last commit date, tracked edits not yet committed,
untracked file count, root commit, entry points (`app.py`, `manage.py`,
`package.json`, `Dockerfile`, ...), detected stack, README size, and a
suggested status. It runs read-only `git` commands, prints to stdout, writes
nothing, and makes no network calls.

Keep the output out of public places: it lists private paths and remotes.

## 2. Classify

| Status | Evidence |
|---|---|
| **active** | the current copy; recent commits or uncommitted work |
| **dormant** | the current copy, idle past the stale threshold |
| **legacy** | replaced by a newer project; record which one (`superseded_by`) |
| **duplicate** | same history (root commit) or remote as another folder; record `duplicate_of` |
| **vendored** | a third-party project; remote owner isn't you or your org |
| **stub** | placeholder or plan; almost no code and no entry point |
| **empty** | no files |
| **not-a-project** | data, assets, installers, a container of other projects |

The script's status is a suggestion. Confirm these by hand:

- **Same history isn't always a duplicate.** A development checkout and a
  production checkout of one repo are both legitimate. Mark them by
  environment instead.
- **Legacy needs a reason.** Shared history only says the folders are related.
  The newest isn't automatically the one in use; check which one a scheduler,
  service or teammate actually runs.
- **Vendored can be yours.** Forks and organisation repos look foreign to a
  single-owner check, so pass every owner you use.
- **Activity signals lie.** Tools that touch every folder (formatters,
  scaffolders, sync clients) reset file timestamps and add untracked files.
  Prefer the last commit date, and count tracked edits rather than untracked
  files.

## 3. Describe from the code

Write one or two sentences per project: what it does and what it touches
(APIs, databases, folders, services). Get it from the code, not the README:

- READMEs are often empty, a template, or describe an earlier version.
- `main.py` containing only `print("Hello from <name>!")` is the `uv init`
  stub; the script flags it. The real entry point is elsewhere (`app.py`, a
  CLI module, a `streamlit run` target). Record that in the notes.
- Read the entry point, the dependency file, and the config or `.env.example`
  for the services it calls. Never copy secret values into the inventory; name
  the variables instead.

## 4. Record it

Use a structured file (YAML or JSON), one entry per folder, with fields such as
`name`, `path`, `description`, `status`, `stack`, `repo`, `superseded_by`,
`duplicate_of`, `environment`, `category` and `notes`. If a tool rewrites the
file, keep information in fields, not comments, because serializers drop
comments.

Keep two lists: projects worth running or tracking, and everything else with
the reason it's excluded (data folder, scratch, empty). A folder that's in
neither list hasn't been looked at.

Flag in `notes` anything dangerous to start: tools that delete data, print
secrets, or act on production. Don't give those a default start command.

## 5. Clean up only with approval

`legacy`, `duplicate`, `empty` and `stub` are cleanup candidates, not cleanup
instructions. Before deleting or moving anything:

- check for uncommitted and unpushed work (`git status`, `git log @{u}..`);
- check for ignored local state git can't restore (`.env`, databases, data
  folders, logs);
- list exactly what would be removed, and get a go-ahead for that list.

Archive rather than delete when in doubt.

## 6. Keep it current

Re-run the scan periodically and diff it against the recorded inventory: new
folders, folders that disappeared, and status changes. Update the record in the
same change that adds or retires a project.

## Data safety and destructive actions

Applies to every AI assistant working in this repository.

- **Least privilege**: touch only the files and paths the task needs. Never
  widen a secret's or API key's scope beyond the task.
- **Environment separation**: production is marked by `<how: env var / tag /
  profile / host>`. Flag it explicitly before running against it, editing its
  config, or including it in a bulk action.
- **Read-only first**: inspect or list before mutating. Don't chain a
  destructive step onto a read step without pausing for confirmation.
- **Approval gates**: never run `<project's destructive commands, e.g. rm -rf,
  git reset --hard, force-push, db reset, deploy --prod>` without stating the
  action and getting a go-ahead first. These have no confirmation prompt of
  their own.
- **Dry-run first**: `<commands that support --dry-run / plan / check>`. Use
  them before a first-time or bulk action. If an action has no dry-run, say so
  before running it for real.
- **Backups**: snapshot before mutating `<config / state / data files>`.
- **Recovery**: `<paths>` are git-tracked and recoverable through git history.
  `<paths, e.g. .env, local db, logs>` are not tracked anywhere. Treat their
  loss as unrecoverable and say so first.
- **Audit trail**: state exactly what was added, changed or deleted. Nothing
  else records it.
- **Kill switches**: `<stop commands>` stop processes, not data, but can lose
  in-flight work. Warn before stopping more than one.

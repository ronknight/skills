# Changelog

## [Unreleased]

### Added
#### 2026-10-12 - api-audit skill
A vendor-neutral method for auditing a poorly documented third-party API. It contains no findings about any specific API.

- **`skills/api-audit/`** - audit workflow, report template, and `postman_inventory.py` (lists requests, flags literal credentials).

#### 2026-10-12 - Initial skills
First four skills, written as generic practice with no project-specific details.

- **`skills/definition-of-done/`** - docs-with-code checklist, ADR template, `snapshot.sh` / `snapshot.ps1`.
- **`skills/ai-safety-guardrails/`** - destructive-action gates and an `AGENTS.md` section template.
- **`skills/excel-com-safe-write/`** - guarded, verified Excel COM writes; `Set-ExcelCells.ps1`.
- **`skills/html-email-jinja/`** - email HTML rules, strict Jinja rendering, skeleton template, `lint_email.py`.
- **`scripts/check-private-terms.sh`** - pre-commit scan against a local, git-ignored list of private terms.

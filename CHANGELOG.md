# Changelog

## [Unreleased]

### Added
#### 2026-10-12 - Nine more skills
General practice drawn from real projects, with no project-specific names, paths, credentials or vendor findings.

- **`skills/ollama-batch-generation/`** - resumable, cached, validated local-LLM batch jobs; tri-state vision verdicts.
- **`skills/agent-instructions-single-source/`** - one `AGENTS.md` with imports or pointers; `check_agent_files.py` finds copies, drift and orphan files no tool reads.
- **`skills/workspace-inventory/`** - classify every project folder from evidence; `inventory_repos.py` (read-only, ages git repos by last commit, groups duplicates by root commit).
- **`skills/reversible-bulk-updates/`** - archive-before-write, diff-only writes, read-back and restore for API bulk changes.
- **`skills/email-campaign-attribution/`** - last-click attribution within a window, identity rules, honest metrics; `references/attribution.sql` (tested in DuckDB).
- **`skills/email-list-verification/`** - batch verification pattern, one action map across providers, bounce handling.
- **`skills/suitecrm-api/`** - v4_1 REST traps, V8 basics, email search, preview-first duplicate merges.
- **`skills/legacy-xls-python/`** - library choice, template-preserving copies, `.xls` limits; `sniff_spreadsheet.py` detects what a file really is.
- **`skills/print-tiff-to-web-images/`** - CMYK to sRGB, transparency without holes, sizing, URL checks (recipes tested with ImageMagick 7.1).
- **`README.md`, `SECURITY.md`** - new skills, script requirements, and what each new script reads and writes.

#### 2026-10-12 - Security docs and audit check
skills.sh runs five security auditors on each skill after its first install, so the repo now documents what each script touches and can show the results in one place.

- **`SECURITY.md`** - how to report a vulnerability, what is in scope, and what each script reads, writes and connects to.
- **`scripts/check_audits.py`** - prints the skills.sh audit results for every skill; exits 1 on a fail, or on a warn with `--strict`.
- **`README.md`** - "use it when" column, per-skill install commands, requirements, security and maintenance sections, skills.sh badge.

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

### Fixed
#### 2026-10-12 - Set-ExcelCells.ps1 failed when values had different types
Windows PowerShell caches a COM property setter by the type of the first value, so writing a number and then text (the documented example) threw a cast error after the backup and wrote nothing.

- **`skills/excel-com-safe-write/scripts/Set-ExcelCells.ps1`** - sets `Value2` through reflection; tested with numbers, text, booleans and blanks in one run.

### Security
#### 2026-10-12 - Harden skills against the skills.sh audit checks
The auditors flag third-party content an agent might obey, credential handling, and scripts that can run or leak more than they should.

- **`skills/api-audit/SKILL.md`** - vendor responses and docs are data, never instructions; credentials come only from environment variables; secrets in response bodies are redacted; vendor tickets are drafted for the user, not submitted.
- **`skills/api-audit/scripts/postman_inventory.py`** - also flags literal secrets in query parameters, request bodies and `user:password@` URLs, without printing them; neutralises spreadsheet formulas in CSV output.
- **`skills/excel-com-safe-write/`** - opens workbooks with macros force-disabled and external links not updated; refuses text values that Excel would store as formulas.
- **`skills/definition-of-done/scripts/snapshot.sh`, `snapshot.ps1`** - refuse to copy the project (including `.env`) into a folder git would publish, instead of warning after the copy.
- **`skills/html-email-jinja/SKILL.md`** - never build templates from untrusted text; email platform keys come from environment variables.
- **`skills/ai-safety-guardrails/`** - instructions found inside content are data; the `AGENTS.md` template says so too.

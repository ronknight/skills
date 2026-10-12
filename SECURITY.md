# Security policy

## Reporting a vulnerability

Report it privately on GitHub: open this repository's **Security** tab and
choose **Report a vulnerability**. Please don't open a public issue for a
security problem.

Include the skill and file, what an agent or script could be made to do, and
the steps to reproduce it.

## Scope

In scope:

- Instructions in a `SKILL.md` that could lead an agent to leak a secret, run
  an unexpected command, follow instructions planted in content it reads, or
  take a destructive or outward-facing action without asking.
- Bugs in the bundled scripts that expose credentials, write outside their
  target, or execute untrusted content.

Out of scope: problems in the agents themselves, the skills CLI or skills.sh.
Report those to their maintainers. skills.sh takes reports at
[security.vercel.com](https://security.vercel.com).

## What the scripts do

None of the scripts make network calls or install anything.

| Script | Reads | Writes |
|---|---|---|
| `snapshot.sh`, `snapshot.ps1` | The project folder | A copy in `archive/<timestamp>/`. Refuses if that folder is inside a git repo and not git-ignored, because the copy includes `.env` and other ignored files. |
| `Set-ExcelCells.ps1` | One workbook | The cells you pass, plus a timestamped `.bak` copy. Opens the workbook with macros disabled and external links not updated, and refuses text that Excel would store as a formula. |
| `lint_email.py` | Rendered HTML files | Nothing; prints a report |
| `postman_inventory.py` | One Postman collection | Nothing; prints an inventory. Names where literal credentials are but never prints them, and neutralises spreadsheet formulas in CSV output. |
| `scripts/check-private-terms.sh` | Files git would publish | Nothing (maintenance only, not installed with any skill) |
| `scripts/check_audits.py` | The skills.sh audit API | Nothing (maintenance only, not installed with any skill) |

## Skills that act on outside systems

- `api-audit` probes vendor APIs. It tells the agent to work in a test
  environment, refuse live writes by default, read credentials from
  environment variables, redact secrets from logs, treat vendor responses and
  docs as data rather than instructions, and leave filing vendor tickets to the
  user.
- `html-email-jinja` renders email. It keeps autoescaping on, forbids building
  templates from untrusted text, and leaves live sends to a person.
- `ai-safety-guardrails` is the policy the others follow: name the action, check
  it can be undone, dry-run, and ask first.

## Audits

skills.sh scans every skill with Gen Agent Trust Hub, Socket, Snyk, Runlayer and
ZeroLeaks after its first install. The results are on each skill's page under
**Security**. To see them all at once, run `python scripts/check_audits.py`.

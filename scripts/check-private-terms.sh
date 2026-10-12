#!/usr/bin/env bash
# Block private terms from reaching this public repo.
# Reads .private-terms.txt (git-ignored, one term per line, # for comments) and
# fails if any term appears in the name or content of a file git would publish
# (tracked or untracked, not ignored). Also flags e-mail addresses and
# user-profile paths. Any tool error fails the check; it never passes by default.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2

TERMS_FILE=".private-terms.txt"
if [ ! -s "$TERMS_FILE" ]; then
    echo "Missing $TERMS_FILE: add one private term per line (the file is git-ignored)." >&2
    exit 1
fi

terms="$(mktemp)"
trap 'rm -f "$terms"' EXIT
grep -v '^[[:space:]]*#' "$TERMS_FILE" | sed 's/[[:space:]]*$//; /^$/d' | tr '[:upper:]' '[:lower:]' > "$terms"

found=0
# grep-style exit codes: 0 = match, 1 = no match, anything else = error.
check() {
    local label="$1"; shift
    "$@"
    local rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "^^ $label" >&2
        found=1
    elif [ "$rc" -gt 1 ]; then
        echo "ERROR: $label check failed to run (exit $rc)" >&2
        exit 2
    fi
}

names_match() {
    git ls-files --cached --others --exclude-standard | tr '[:upper:]' '[:lower:]' | grep -F -f "$terms"
}

check "private term in file content" git grep --untracked -n -i -F -f "$terms"
check "private term in file name" names_match
check "e-mail address" sh -c "git grep --untracked -n -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' | grep -viE '@(example\.(com|org|net)|users\.noreply\.github\.com)'"
check "user-profile path" git grep --untracked -n -i -E -e '[a-z]:[\\/]+users[\\/]+' -e '/home/[a-z]' -e '/users/[a-z]'

if [ "$found" -ne 0 ]; then
    echo "Remove the matches above before committing." >&2
    exit 1
fi
echo "Private-terms check passed."

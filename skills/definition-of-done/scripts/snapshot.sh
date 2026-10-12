#!/usr/bin/env bash
# Copy a project into archive/<YYYY-MM-DD_HHmmss>/ as a local restore point.
# Usage: snapshot.sh [project_dir] [archive_dir]
set -euo pipefail

PROJECT_DIR="$(cd "${1:-.}" && pwd)"
ARCHIVE_DIR="${2:-$PROJECT_DIR/archive}"
mkdir -p "$ARCHIVE_DIR"
ARCHIVE_DIR="$(cd "$ARCHIVE_DIR" && pwd)"
DEST="$ARCHIVE_DIR/$(date +%Y-%m-%d_%H%M%S)"

if [ -e "$DEST" ]; then
    echo "Snapshot already exists: $DEST" >&2
    exit 1
fi
mkdir "$DEST"

# Bare names match at any depth; ./names match the top level only.
EXCLUDES=(.git .venv venv __pycache__ '*.pyc' .DS_Store node_modules
          .pytest_cache .mypy_cache .ruff_cache
          ./archive ./build ./dist ./target)
case "$ARCHIVE_DIR" in
    "$PROJECT_DIR"/*) EXCLUDES+=("./${ARCHIVE_DIR#"$PROJECT_DIR"/}") ;;
esac

TAR_ARGS=()
for pattern in "${EXCLUDES[@]}"; do
    TAR_ARGS+=("--exclude=$pattern")
done

(cd "$PROJECT_DIR" && tar "${TAR_ARGS[@]}" -cf - .) | (cd "$DEST" && tar -xf -)

if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if ! git -C "$PROJECT_DIR" check-ignore -q "$DEST"; then
        echo "WARNING: $DEST is not git-ignored. Add 'archive/' to .gitignore;" \
             "the snapshot includes ignored files such as .env." >&2
    fi
fi

echo "Snapshot created: $DEST ($(find "$DEST" -type f | wc -l | tr -d ' ') files)"

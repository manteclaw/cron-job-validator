#!/bin/bash
# with-lock.sh — Wrapper to prevent concurrent execution of cron scripts
# Usage: bash with-lock.sh <script_path> [script_args...]
# Creates lock at $WITH_LOCK_DIR/$(basename script).lock
#
# Configuration (environment variables):
#   WITH_LOCK_BASE  base directory the script path is resolved against,
#                   and where .env is read from (default: current directory)
#   WITH_LOCK_DIR   lock directory (default: $WITH_LOCK_BASE/.state/locks)

set -e

BASE_DIR="${WITH_LOCK_BASE:-$PWD}"
LOCK_DIR="${WITH_LOCK_DIR:-$BASE_DIR/.state/locks}"

# Source .env generically: every KEY=value in it is exported to the child.
# List your own variables in your .env — nothing is hardcoded here.
if [ -f "$BASE_DIR/.env" ]; then
    set -a
    . "$BASE_DIR/.env"
    set +a
fi

mkdir -p "$LOCK_DIR"

if [ $# -lt 1 ]; then
    echo "Usage: with-lock.sh <script> [args...]"
    exit 1
fi

SCRIPT="$1"
SCRIPT_NAME=$(basename "$SCRIPT" | sed 's/[^a-zA-Z0-9._-]/_/g')
LOCK_FILE="$LOCK_DIR/${SCRIPT_NAME}.lock"
PID_FILE="$LOCK_DIR/${SCRIPT_NAME}.pid"

# Check for stale lock
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[$(date)] SKIP: $SCRIPT_NAME already running (PID $OLD_PID)"
        exit 0
    fi
    echo "[$(date)] Stale lock found for $SCRIPT_NAME, removing"
    rm -f "$LOCK_FILE" "$PID_FILE"
fi

# Acquire lock
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "[$(date)] SKIP: Could not acquire lock for $SCRIPT_NAME"
    exit 0
fi

# Write PID
echo $$ > "$PID_FILE"

# Run the script (absolute paths are used as given; relative paths
# resolve against $BASE_DIR)
shift
case "$SCRIPT" in
    /*) "$SCRIPT" "$@" ;;
    *)  "$BASE_DIR/$SCRIPT" "$@" ;;
esac
EXIT_CODE=$?

# Cleanup
rm -f "$PID_FILE"

exit $EXIT_CODE

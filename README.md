# cron-job-validator

Pre-flight checks for a crontab full of scheduled jobs, aimed at the two ways
cron fails *silently* — no error, no output, just work that never happened.

## The two silent-failure modes

1. **The script isn't there anymore.** You renamed, moved, or deleted a
   script; the crontab still points at the old path. Cron runs nothing and
   tells no one. Weeks later you notice the job's output stopped.
2. **Two copies run at once.** A job runs longer than its interval, the next
   scheduled copy starts on top of it, and both write to the same files,
   queues, or wallets. Cron has no built-in overlap protection.

`validate-cron.py` covers mode 1. `with-lock.sh` covers mode 2.

## Who it's for

Anyone running more than a handful of cron-scheduled scripts — especially
agent operators whose whole estate is dozens of unattended jobs, where a
silently dead job can mean a silently dead income stream or monitor.

## validate-cron.py

Parses a crontab file, extracts every `python3 scripts/...` /
`bash scripts/...` reference, and reports which ones are missing or not
executable — before cron silently runs nothing.

```console
$ python3 validate-cron.py --workspace ~/my-agent --crontab ~/my-agent/crontab.txt
📋 Found 14 unique scripts in crontab

🔴 MISSING (1):
  scripts/old-monitor.py

🟡 NOT EXECUTABLE (1):
  scripts/nightly-report.sh

$ python3 validate-cron.py --fix   # chmod +x the fixable ones
```

Exit code is 1 when anything is missing, 0 otherwise — wire it into a
deploy script or a daily health check.

Configuration (flags win over environment):

| Setting | Flag | Env var | Default |
|---|---|---|---|
| Workspace base | `--workspace` | `CRON_WORKSPACE` | `.` |
| Crontab file | `--crontab` | `CRON_TAB_FILE` | `<workspace>/crontab.txt` |

Notes on what counts as a failure:

- `.py` files invoked via `python3` do **not** need the executable bit, so
  they are only reported when missing.
- Shell scripts invoked via `bash scripts/x.sh` *do* get flagged when not
  executable if your crontab later calls them directly — and `--fix`
  chmods them either way when flagged. (If you always invoke via `bash`,
  treat the warning as informational.)

## with-lock.sh

A flock-based wrapper: wrap a cron command and a second copy started while
the first is still running exits quietly instead of piling on.

```cron
*/10 * * * * bash /path/to/with-lock.sh scripts/my-job.sh
```

- Lock and PID files live in `$WITH_LOCK_DIR` (default
  `<base>/.state/locks`), one per script name.
- A stale lock from a crashed run is detected via the recorded PID and
  cleared automatically.
- If `$WITH_LOCK_BASE/.env` exists it is sourced generically — every
  variable in it is exported to the wrapped script. Put your own keys
  there; the wrapper hardcodes none.
- Exit code of the wrapped script is passed through.

| Setting | Env var | Default |
|---|---|---|
| Base directory | `WITH_LOCK_BASE` | current directory |
| Lock directory | `WITH_LOCK_DIR` | `$WITH_LOCK_BASE/.state/locks` |

See `.env.example` for all of the above in copy-paste form.

## Honest limits

- The validator only recognises `python3 scripts/...` and `bash scripts/...`
  references — the convention in the crontabs it was written for. Jobs that
  call scripts by absolute path, via other interpreters, or through shell
  indirection are not seen. Extending the regex is a one-line change.
- It checks existence and the executable bit, nothing more: a script that
  exists, is executable, and is itself broken passes. This is a pre-flight
  for *silent* failures, not a test suite.
- `with-lock.sh` prevents overlap of the *same* script name. Two different
  wrappers around the same underlying job will not see each other.

## License

MIT — see `LICENSE`.

#!/usr/bin/env python3
"""
Cron Validation — Verify all scripts referenced in a crontab exist and are executable.

Usage:
    python3 validate-cron.py [--fix] [--crontab PATH] [--workspace DIR]

Configuration (CLI flags win over environment variables):
    --crontab PATH / CRON_TAB_FILE   crontab file to parse
                                     (default: <workspace>/crontab.txt)
    --workspace DIR / CRON_WORKSPACE base directory that the relative
                                     scripts/... paths in the crontab are
                                     resolved against (default: .)
    --fix                            chmod +x the scripts that are fixable
"""

import argparse, os, re, sys

def parse_crontab(crontab_file):
    scripts = set()
    with open(crontab_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Extract script path after the interpreter
            # Match patterns like: ... python3 scripts/foo.py ... or bash scripts/foo.sh ...
            matches = re.findall(r'(?:python3|bash)\s+(scripts/\S+)', line)
            for m in matches:
                scripts.add(m)
    return sorted(scripts)

def check_scripts(scripts, workspace):
    missing = []
    not_executable = []

    for s in scripts:
        path = os.path.join(workspace, s)
        if not os.path.exists(path):
            missing.append(s)
        elif os.access(path, os.X_OK):
            # OK
            pass
        elif s.endswith(".py"):
            # Python scripts don't need +x if called with python3
            pass
        else:
            not_executable.append(s)

    return missing, not_executable

def fix_executable(scripts, workspace):
    for s in scripts:
        path = os.path.join(workspace, s)
        os.chmod(path, os.stat(path).st_mode | 0o755)
        print(f"  +x {s}")

def main():
    parser = argparse.ArgumentParser(description="Verify scripts referenced in a crontab exist and are executable.")
    parser.add_argument("--fix", action="store_true", help="chmod +x fixable scripts")
    parser.add_argument("--crontab", default=os.environ.get("CRON_TAB_FILE"),
                        help="crontab file to parse (default: <workspace>/crontab.txt)")
    parser.add_argument("--workspace", default=os.environ.get("CRON_WORKSPACE", "."),
                        help="base directory for relative script paths (default: .)")
    args = parser.parse_args()

    crontab_file = args.crontab or os.path.join(args.workspace, "crontab.txt")

    scripts = parse_crontab(crontab_file)
    print(f"📋 Found {len(scripts)} unique scripts in crontab")

    missing, not_exec = check_scripts(scripts, args.workspace)

    if missing:
        print(f"\n🔴 MISSING ({len(missing)}):")
        for s in missing:
            print(f"  {s}")

    if not_exec:
        print(f"\n🟡 NOT EXECUTABLE ({len(not_exec)}):")
        for s in not_exec:
            print(f"  {s}")
        if args.fix:
            print("\n🔧 Fixing...")
            fix_executable(not_exec, args.workspace)

    if not missing and not not_exec:
        print("\n✅ All scripts present and executable")
        return 0

    return 1 if missing else 0

if __name__ == "__main__":
    sys.exit(main())

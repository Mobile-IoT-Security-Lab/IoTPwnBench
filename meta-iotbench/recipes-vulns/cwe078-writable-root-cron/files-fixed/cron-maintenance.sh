#!/bin/sh
# Root maintenance job, corrected variant of CWE-78. TARGET is data, never a command.
TARGET="$(cat /var/lib/router-dashboard/maintenance-target 2>/dev/null)"
printf 'maintenance target: %s\n' "$TARGET" \
    > /var/lib/router-dashboard/cron-last-run.txt 2>&1

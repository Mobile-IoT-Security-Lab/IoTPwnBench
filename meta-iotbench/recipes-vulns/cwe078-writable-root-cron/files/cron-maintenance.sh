#!/bin/sh
# INTENTIONALLY VULNERABLE LAB JOB.
# The web service controls TARGET and root passes it to a shell command.
TARGET="$(cat /var/lib/router-dashboard/maintenance-target 2>/dev/null)"
/bin/sh -c "printf 'maintenance target: %s\\n' ${TARGET}" \
    > /var/lib/router-dashboard/cron-last-run.txt 2>&1

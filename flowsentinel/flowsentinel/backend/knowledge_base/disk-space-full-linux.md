# Disk Space Full on Linux Servers

## Symptoms
"No space left on device", failed deployments or pipelines, services crashing, logs not written, build runners failing.

## Steps
1. Check usage per filesystem with `df -h` and inodes with `df -i`; an inode shortage looks identical.
2. Find the largest directories: `du -xh / --max-depth=2 2>/dev/null | sort -h | tail -20`.
3. Typical culprits: old logs in /var/log, Docker images and build cache, CI workspaces, core dumps and package caches.
4. Safe cleanup: `journalctl --vacuum-size=500M`, `docker system prune -af --volumes` (confirm no needed volumes first), remove old CI workspaces, `apt-get clean`.
5. If a deleted file is still held open, space is not freed: find it with `lsof +L1` and restart the owning service.
6. Restart failed services and re-run the failed pipeline.

## Prevent recurrence
Configure logrotate, set a disk usage alert at 80 percent, and add a scheduled prune job for build runners.

## Escalate if
The root filesystem is full on a production database server or the volume cannot be extended.

# PostgreSQL Connection Pool Exhaustion and Database Unresponsive

## Symptoms
Applications return "too many connections", "connection pool exhausted" or time out. The database primary seems down or slow and many users see errors.

## Immediate triage
1. Check that the PostgreSQL service is running and the host has free memory and disk space.
2. Count connections: `SELECT count(*), state FROM pg_stat_activity GROUP BY state;` and compare with `max_connections`.
3. Look for long-running or idle-in-transaction sessions: `SELECT pid, now()-xact_start AS age, query FROM pg_stat_activity WHERE state <> 'idle' ORDER BY age DESC;`
4. Terminate the blocking or runaway sessions with `SELECT pg_terminate_backend(pid);` after confirming they are not a critical batch job.
5. Check for lock contention and deadlocks in `pg_locks` and the PostgreSQL log.

## Restore service
1. Restart the application pods or pool (PgBouncer) to release leaked connections.
2. If the primary is unreachable, promote the healthiest replica following the failover runbook and repoint the application.
3. Confirm replication lag is zero before declaring recovery.

## Prevent recurrence
Set `idle_in_transaction_session_timeout`, size application pools below `max_connections`, and put PgBouncer in front of the database.

## Escalate if
The primary does not accept connections after a restart or data corruption is suspected: page the Database Administration on-call immediately.

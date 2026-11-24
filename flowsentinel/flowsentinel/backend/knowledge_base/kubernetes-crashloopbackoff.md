# Kubernetes Pod CrashLoopBackOff

## Symptoms
A pod restarts repeatedly and shows `CrashLoopBackOff`, often right after a deployment. The service has fewer healthy replicas or none.

## Diagnose
1. `kubectl get pods -n <namespace>` and note the restart count.
2. `kubectl describe pod <pod>` and read the Events and the last state; look for OOMKilled, exit codes and failing probes.
3. `kubectl logs <pod> --previous` to read the output of the crashed container.
4. Compare the new deployment against the last working release: image tag, environment variables, secrets and config maps.

## Common causes and fixes
1. Missing or wrong environment variable or secret: fix the config and redeploy.
2. OOMKilled (exit code 137): raise the memory limit or fix the leak.
3. Failing liveness or readiness probe: correct the probe path and increase `initialDelaySeconds`.
4. Bad image or migration failure: roll back with `kubectl rollout undo deployment/<name>`.

## Escalate if
Rollback does not restore service or the production cluster nodes are unhealthy: escalate to Platform / SRE.

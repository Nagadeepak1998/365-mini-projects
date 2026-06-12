# AI Runbook Response

The payment-api incident appears tied to a CrashLoopBackOff during a recent rollout. The strongest evidence is the readiness probe failure and connection refused messages, so the response should stay focused on pod health, probe behavior, and recent deployment changes.

Recommended sequence:

1. Capture current pod evidence with `kubectl describe pod` and `kubectl logs --previous` before restarting anything.
2. Check `kubectl rollout history deployment/payment-api` and compare the deployment revision with the first failing timestamp.
3. Validate the readiness probe path, startup timing, health endpoint behavior, and dependency endpoint availability.
4. If the new revision introduced the failure, roll back to the previous known-good revision and keep the failed pod logs attached to the incident.

Do not claim a final root cause until the pod events, previous logs, and rollout history agree.

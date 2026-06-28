Built a small ECS service safety checker today.

The script reviews a saved ECS service inventory for rollout settings that are easy to miss: low task count, missing circuit breaker rollback, risky deployment percentages, weak health checks, missing CPU or memory alarms, mutable task images, short log retention, and missing owners.

I kept it dependency-free with safe and risky samples plus unit tests, so it works as a local preflight check before trusting a production service rollout.

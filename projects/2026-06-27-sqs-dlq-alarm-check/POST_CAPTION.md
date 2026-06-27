Today I built a small SQS DLQ alarm checker.

The idea is simple: a dead-letter queue is not enough by itself. The queue needs an owner, the source queue needs a redrive policy, the DLQ needs an alarm, and the alarm needs a threshold and runbook that are useful when support is actually looking at it.

I kept it dependency-free with safe and risky JSON fixtures, unit tests, and clear exit codes so it can be run from a static inventory export.

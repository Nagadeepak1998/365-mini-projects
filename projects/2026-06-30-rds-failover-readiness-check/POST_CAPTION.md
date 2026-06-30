Today I added a small RDS failover readiness checker to my 365 mini-projects repo.

The idea is simple: before treating a production database as ready for failover, I want a quick way to review the basics from an inventory snapshot. The CLI checks ownership, Multi-AZ coverage, backups, deletion protection, key alarms, replica lag coverage, failover drill evidence, RTO/RPO notes, and pending-reboot changes.

What I liked about this one is that it turns a vague question like "are we ready if this database fails over?" into a concrete checklist with deterministic sample inputs and unit tests.

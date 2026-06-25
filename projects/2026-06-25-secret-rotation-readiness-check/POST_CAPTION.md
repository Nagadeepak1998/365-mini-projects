Today I built a small secret rotation readiness checker.

The idea is simple: before rotating credentials, review the parts that usually cause production risk. The CLI checks stale secrets, overdue rotation dates, missing owners, missing rollback plans, weak validation evidence, and critical-path secrets that cannot support old/new credential overlap.

I kept it dependency-free with JSON fixtures and unit tests so it is easy to run locally and easy to explain.

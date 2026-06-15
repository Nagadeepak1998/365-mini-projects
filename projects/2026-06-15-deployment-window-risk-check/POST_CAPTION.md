Today I built a small deployment-window risk checker.

It reviews a production deployment plan for the release details that can quietly create incidents: freeze-window overlap, all-at-once rollout strategy, weak rollback planning, database migration risk, low error budget, missing monitoring links, and recent incident pressure.

The project is a Python CLI with sample deployment plans and unit tests. It is intentionally simple, but it models the kind of pre-release thinking I want to keep practicing for DevOps, SRE, and platform engineering work.

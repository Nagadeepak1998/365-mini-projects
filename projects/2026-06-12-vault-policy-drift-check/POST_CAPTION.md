# GitHub / LinkedIn Post Caption

Built a small but practical DevSecOps project today: **Vault Policy Drift Check**.

It reviews a candidate Vault ACL policy against a known-good baseline and flags risky drift like wildcard writes, new write-capable paths, and expanded access on sensitive `sys/*`, `auth/*`, and production secret paths.

Why I like this kind of project:

- deterministic and CI-friendly
- no paid APIs or cloud setup required
- directly useful for platform and security review workflows
- easy to explain in interviews because the problem is real

Tech: Python, policy parsing, CLI automation, security guardrails, test coverage.

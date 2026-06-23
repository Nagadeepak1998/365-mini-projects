Built a small feature flag rollout checker today.

It compares the current and proposed flag config, then flags rollout jumps, missing owners, missing cleanup dates, debug behavior in prod, and missing kill switches. This was a useful practice project because feature flags are supposed to reduce release risk, but they still need ownership and rollback discipline.

Verified with unit tests plus safe and risky JSON samples.

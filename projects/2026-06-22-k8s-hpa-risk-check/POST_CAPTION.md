Built a small Kubernetes HPA risk checker today.

It reads a `kubectl` JSON snapshot and flags autoscaling settings that can surprise a team during production support: no scale-out room, CPU metrics without CPU requests, missing scale targets, low minimum replicas, and no scale-down stabilization window.

The useful part for me was turning operational review questions into deterministic checks I can run before a release instead of relying on memory during a handoff.

# Container Image Drift Check

Container Image Drift Check is a small Python CLI I built to review Kubernetes workload snapshots for image pinning and version drift problems.

## Problem

Container images can drift even when Kubernetes manifests look valid. A workload might use `latest`, skip digest pinning, or run the same image repository at different tags across namespaces. Those changes are easy to miss in a review and can make rollbacks or incident analysis harder.

I wanted a quick local check I could run against a `kubectl` snapshot before a deployment review.

## What It Does

- reads `kubectl get deployment,statefulset,daemonset,cronjob -A -o json` output
- flags images without digest pinning
- flags untagged images and mutable tags such as `latest`, `canary`, `dev`, and `nightly`
- flags mutable tags combined with sticky pull policies such as `IfNotPresent`
- flags the same image repository running with multiple tags or digests in one snapshot
- checks regular containers and init containers

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for verification

## Folder Structure

```text
.
|-- README.md
|-- container_image_drift_check.py
|-- samples
|   |-- risky_workloads.json
|   `-- safe_workloads.json
`-- tests
    `-- test_container_image_drift_check.py
```

## How to Run

From this project folder:

```bash
python3 container_image_drift_check.py samples/risky_workloads.json
```

Expected result:

```text
FLAGGED: 10 container image drift issue(s)
```

Check the safer sample:

```bash
python3 container_image_drift_check.py samples/safe_workloads.json
```

Expected result:

```text
PASS: no container image drift risks detected
```

Return JSON instead:

```bash
python3 container_image_drift_check.py samples/risky_workloads.json --format json
```

Use it with a real cluster snapshot:

```bash
kubectl get deployment,statefulset,daemonset,cronjob -A -o json > workload-images.json
python3 container_image_drift_check.py workload-images.json
```

## Example

The risky sample includes:

- a production deployment using `latest`
- a mutable tag with `imagePullPolicy: IfNotPresent`
- an untagged worker image
- a CronJob using a `nightly` tag
- the same API image repository running with different versions across namespaces

Those are the kinds of image hygiene problems I want to catch before a rollout starts.

## Tests

```bash
python3 -m py_compile container_image_drift_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

- This is a static review tool, not a replacement for admission control or image signing.
- Digest pinning is intentionally treated as the safer default because it makes deploys easier to reproduce.
- The drift check is snapshot-based, so it is most useful when the JSON includes all relevant namespaces for the service.

# Release Artifact Provenance Check

I built this small CLI to turn release supply-chain evidence into a deterministic promotion check. It reviews a normalized JSON inventory, so it can sit after artifact metadata collection without needing registry or CI credentials.

## What it does

The checker flags artifacts with missing ownership, invalid SHA-256 digests, missing or unsupported SBOMs, unverified signatures or build provenance, missing source identity, and production promotions whose digest was not matched.

## How to run

```bash
python3 release_artifact_provenance_check.py samples/safe_inventory.json
python3 release_artifact_provenance_check.py samples/risky_inventory.json
python3 release_artifact_provenance_check.py samples/risky_inventory.json --json
```

A clean inventory exits `0`, findings exit `1`, and invalid input exits `2`.

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Notes

This tool checks recorded evidence; it does not independently query a registry or verify a cryptographic signature. That separation keeps the example dependency-free while making the trust boundary explicit: an upstream CI step must collect and verify the evidence honestly.

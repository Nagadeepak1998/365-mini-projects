# TLS Certificate Readiness Check

I built this small CLI to review a saved TLS certificate inventory before expiry becomes an outage. Certificate renewals are easy to forget until they are urgent, so this focuses on the checks I would want before a public production endpoint is close to renewal.

## What It Does

The script reads a JSON inventory and flags public production certificates with:

- missing owners
- expired or soon-to-expire certificates
- near-expiry certificates without auto-renewal enabled
- missing hostname/SAN validation
- missing certificate chain validation
- missing renewal runbooks
- missing expiry alarms
- key sizes below 2048 bits
- SHA-1 signature algorithms
- missing or stale rotation drill dates

It exits with `0` when the inventory is ready, `1` when it finds issues, and `2` for invalid input.

## How To Run

```bash
python3 tls_certificate_readiness_check.py samples/safe_inventory.json --today 2026-07-08
```

Expected output:

```text
PASS: TLS certificate inventory looks ready
```

Risky sample:

```bash
python3 tls_certificate_readiness_check.py samples/risky_inventory.json --today 2026-07-08
```

Expected output starts with:

```text
FLAGGED: 12 TLS certificate readiness issue(s) detected
```

## Input Shape

```json
{
  "certificates": [
    {
      "common_name": "api.example.com",
      "environment": "prod",
      "exposure": "public",
      "owner": "platform-edge",
      "issuer": "Example Managed CA",
      "expires_at": "2026-10-30",
      "auto_renew": true,
      "hostname_match_validated": true,
      "certificate_chain_validated": true,
      "renewal_runbook": "docs/runbooks/tls-renewal.md",
      "monitoring_alarm": "tls-expiry-api-example-com",
      "key_size_bits": 2048,
      "signature_algorithm": "sha256WithRSAEncryption",
      "last_rotation_drill_at": "2026-03-15"
    }
  ]
}
```

## Tests

```bash
python3 -m py_compile tls_certificate_readiness_check.py tests/test_tls_certificate_readiness_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
python3 tls_certificate_readiness_check.py samples/safe_inventory.json --today 2026-07-08
python3 tls_certificate_readiness_check.py samples/risky_inventory.json --today 2026-07-08
```

## Notes

This is a static review tool for saved certificate inventory data. It does not call ACM, Let's Encrypt, a load balancer API, or any live endpoint. I kept it dependency-free so it can run quickly from a local checkout or CI job before a certificate renewal window.

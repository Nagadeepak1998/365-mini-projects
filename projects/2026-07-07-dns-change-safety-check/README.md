# DNS Change Safety Check

I built this small CLI to review DNS change plans before a public production cutover. DNS changes can look simple in a ticket, but a bad TTL, missing rollback plan, apex CNAME, wildcard change, or production delete can make an incident harder to unwind.

## What It Does

The script reads a JSON DNS change plan and flags production public-zone changes with:

- missing owners
- missing ticket or approval references
- destructive deletes without an explicit migration plan
- cutover TTL values above 300 seconds
- existing TTL values high enough to slow rollback
- CNAME records that appear to target the zone apex
- wildcard production records that need manual review
- MX records without a positive priority
- missing rollback plans
- missing validation checks for DNS resolution, HTTP health, or rollback verification

It exits with `0` when the change plan is ready, `1` when it finds issues, and `2` for invalid input.

## How To Run

```bash
python3 dns_change_safety_check.py samples/safe_change_plan.json
```

Expected output:

```text
PASS: DNS change plan looks ready
```

Risky sample:

```bash
python3 dns_change_safety_check.py samples/risky_change_plan.json
```

Expected output starts with:

```text
FLAGGED: 12 DNS change safety issue(s) detected
```

## Input Shape

```json
{
  "changes": [
    {
      "name": "api.example.com",
      "type": "A",
      "action": "update",
      "environment": "prod",
      "zone_scope": "public",
      "owner": "platform-dns",
      "ticket": "CHG-2407",
      "ttl_seconds": 60,
      "existing_ttl_seconds": 300,
      "rollback": "Restore the previous alias target from the change ticket.",
      "validation_checks": [
        {
          "name": "dns_resolution",
          "enabled": true
        },
        {
          "name": "http_health",
          "enabled": true
        },
        {
          "name": "rollback_verified",
          "enabled": true
        }
      ]
    }
  ]
}
```

## Tests

```bash
python3 -m py_compile dns_change_safety_check.py tests/test_dns_change_safety_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

This is a static review tool for saved DNS change data. It does not call Route 53, Cloudflare, or any registrar API. I kept it dependency-free so it can run quickly from a local checkout or CI job before a DNS cutover.

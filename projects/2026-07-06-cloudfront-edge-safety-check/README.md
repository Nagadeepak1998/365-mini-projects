# CloudFront Edge Safety Check

I built this small CLI to review CloudFront distribution inventory before a public edge path is treated as production-ready. It focuses on the controls I would want to see before traffic depends on a distribution: ownership, WAF coverage, modern TLS, HTTPS enforcement, security headers, access logs, failover for critical paths, and basic alarms.

## What It Does

The script reads a JSON inventory of CloudFront distributions and flags production distributions with:

- missing owners
- missing WAF web ACLs
- old or missing minimum TLS policies
- disabled access logging
- access log retention under 30 days
- critical distributions without origin failover
- default or cache behaviors that do not enforce HTTPS
- default or cache behaviors without a response headers policy
- missing enabled alarms for `5xx_error_rate`, `origin_latency`, or `waf_block_spike`

It exits with `0` when the inventory is ready, `1` when it finds issues, and `2` for invalid input.

## How To Run

```bash
python3 cloudfront_edge_safety_check.py samples/safe_inventory.json
```

Expected output:

```text
PASS: CloudFront edge safety looks ready
```

Risky sample:

```bash
python3 cloudfront_edge_safety_check.py samples/risky_inventory.json
```

Expected output starts with:

```text
FLAGGED: 13 CloudFront edge safety issue(s) detected
```

## Input Shape

```json
{
  "distributions": [
    {
      "id": "orders-edge",
      "environment": "prod",
      "owner": "edge-platform",
      "critical": true,
      "web_acl_id": "arn:aws:wafv2:us-east-1:123456789012:global/webacl/orders",
      "minimum_protocol_version": "TLSv1.2_2021",
      "access_logging": {
        "enabled": true,
        "retention_days": 90
      },
      "origin_failover": {
        "enabled": true
      },
      "default_behavior": {
        "viewer_protocol_policy": "redirect-to-https",
        "response_headers_policy": "security-headers"
      },
      "cache_behaviors": [
        {
          "path_pattern": "/api/*",
          "viewer_protocol_policy": "https-only",
          "response_headers_policy": "api-security-headers"
        }
      ],
      "alarms": [
        {
          "name": "5xx_error_rate",
          "enabled": true
        },
        {
          "name": "origin_latency",
          "enabled": true
        },
        {
          "name": "waf_block_spike",
          "enabled": true
        }
      ]
    }
  ]
}
```

## Tests

```bash
python3 -m py_compile cloudfront_edge_safety_check.py tests/test_cloudfront_edge_safety_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

This is a static review tool for saved distribution inventory data. It does not call AWS APIs and it is not a replacement for CloudFront, WAF, or CloudWatch configuration management. I kept it dependency-free so it can run quickly from a local checkout or CI job with an exported edge inventory.

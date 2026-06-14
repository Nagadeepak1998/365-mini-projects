Built a small SLO burn-rate checker today in Python.

It reads a service snapshot with request and error counts, converts that into error-budget burn rate, and flags when short or long windows are consuming the budget too quickly. I like this kind of tool because it turns "the error rate looks bad" into something more operational: how fast would this burn through a 30-day SLO budget?

I kept it simple with sample snapshots, unit tests, and JSON output so it can fit into a local incident review workflow.

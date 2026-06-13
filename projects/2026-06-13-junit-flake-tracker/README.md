# JUnit Flake Tracker

JUnit Flake Tracker is a small Python CLI I built to scan JUnit XML reports and surface three CI signals quickly: tests that flip between pass and fail, tests that fail repeatedly across runs, and tests that are simply too slow.

I wanted something lightweight that I could run locally on archived CI artifacts before digging through a long Actions or Jenkins page.

## Problem

When a pipeline goes red, the first question is often whether the failure is a real regression, an intermittent test, or just a slow test that is starting to hurt the build. JUnit XML reports already contain most of that signal, but it is awkward to compare multiple runs by eye.

## What It Does

- reads one or more JUnit XML report files
- flags tests that both passed and failed across the provided reports
- flags tests that failed repeatedly across multiple reports
- flags tests whose runtime crosses a configurable threshold
- returns text output for humans or JSON output for scripts

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for local verification

## Folder Structure

```text
.
|-- README.md
|-- POST_CAPTION.md
|-- junit_flake_tracker.py
|-- samples
|   |-- run_01.xml
|   |-- run_02.xml
|   `-- stable_run.xml
`-- tests
    `-- test_junit_flake_tracker.py
```

## How to Run

From this project folder:

```bash
python3 junit_flake_tracker.py samples/run_01.xml samples/run_02.xml
```

Expected result:

```text
FLAGGED: 3 issue(s)
```

Check a clean report:

```bash
python3 junit_flake_tracker.py samples/stable_run.xml
```

Expected result:

```text
PASS: no obvious flaky, repeated-failure, or slow-test signals detected
```

Return JSON instead of plain text:

```bash
python3 junit_flake_tracker.py samples/run_01.xml samples/run_02.xml --format json
```

## Example

In the bundled sample reports:

- `tests.api.test_orders::test_checkout_retry` passes in one run and fails in another, so it looks flaky
- `tests.jobs.test_sync::test_backfill_job` fails in both runs, so it looks like a stable failure
- `tests.ui.test_dashboard::test_homepage_render` crosses the slow-test threshold

## Tests

```bash
python3 -m py_compile junit_flake_tracker.py
python3 -m unittest discover -s tests
```

## Notes

- This tool is report-driven, so it works best when you compare a few recent CI runs of the same suite.
- It does not try to infer ownership or root cause. It only packages the signals already present in the reports.
- If I wanted to grow it further, I would add CSV export and support for grouping by suite or package.

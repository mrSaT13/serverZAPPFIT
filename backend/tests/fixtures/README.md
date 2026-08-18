# Test Fixtures

This directory contains fixtures used by the test suite.

## Structure

```
fixtures/
  fit/          - Sample FIT files for activity file import tests
  tcx/          - Sample TCX files for activity file import tests
  gpx/          - Sample GPX files for activity file import tests
  strava/       - JSON payload fixtures for Strava activity/gear/athlete data
  garmin/       - JSON payload fixtures for Garmin activity/health/gear data
  profile/      - ZIP fixtures for profile import/export tests
  README.md     - This file
```

## Conventions

- Keep binary fixtures (FIT, GPX, TCX, ZIP) under 50 KB.
- JSON fixtures should be valid JSON with realistic payloads.
- Prefer synthetic fixtures over real user data.
- All paths in test code should use `Path(__file__).parent.parent / "fixtures"` to locate files.

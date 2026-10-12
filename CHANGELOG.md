# Changelog

## [0.2.1] - 2026-10-11

- Added a one-command verification runner, safe Makefile shortcuts and real-extension synthetic Chromium lifecycle test.
- Added store submission preparation, privacy and listing guidance.
- Added reproducible, validated source, sideload and store-root ZIP packaging.
- No change to the real Facebook publishing controls or existing CLI repository.

## [0.2.0] - 2026-10-11

- Combined the browser-native publishing prototype with a local-first photo library, image metadata removal, scheduling and broader offline tests.
- Added two separate actions: Prepare for review and user-confirmed Change now.
- Kept all scheduled operations review-only. Automatic public Save is disabled for alarms.
- No-repeat rotation now advances after the Save dialog acknowledges closure, never during review-only runs.
- Expanded mock-page tests to cover a Save click, dialog closure, review mode, and missing-input failure.
- Added permission and privacy checks, release documentation and reproducible archives.
- No changes to the separate Python CLI project.

## [0.1.0] - 2026-10-11

- Initial experimental local-first Chrome and Brave Manifest V3 extension.
- Browser-only image library with JPEG re-encoding to remove metadata.
- Random and no-repeat preparation choices.
- Optional daily browser alarm for opening a review dialog.
- Dialog-scoped upload in review-only mode.

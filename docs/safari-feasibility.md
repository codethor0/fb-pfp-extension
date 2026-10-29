# Safari feasibility assessment

Date: 2026-10-29. Scope: what it would take to ship fb-pfp on Safari for
macOS and iOS, based on evidence collected this date. Nothing here has been
run against Safari; every claim carries its source.

## What works in our favor

- The Firefox build already emits the background shape Safari wants:
  `background.scripts` with `type: "module"` as an event page. Safari does
  not run MV3 `background.service_worker`; Apple's own Xcode template uses
  the `scripts` form. The Safari manifest is therefore a small delta on
  `tools/build_firefox.py`, not a new architecture.
- API surface is minimal: `alarms`, `runtime`, `storage`, `tabs`. All four
  exist in Safari Web Extensions on macOS (alarms since Safari 14, per MDN
  browser-compat data checked 2026-10-29).
- `chrome.storage.local.setAccessLevel` is already feature-detected as a
  Chromium-only hardening API, so its absence in Safari is a no-op.
- The content script uses standard DOM APIs only (canvas, createImageBitmap,
  DataTransfer, file inputs); nothing there is Chromium-specific.

## What blocks or degrades

- **iOS has no `alarms` API** (MDN compat data: `safari_ios: None` for every
  alarms member). The optional daily-review schedule cannot work on iPhone
  or iPad. Manual Prepare / Change-now flows could still work. A Safari iOS
  build must degrade the schedule UI honestly or hide it.
- **Distribution requires the Apple Developer Program** (99 USD per year) and
  an Xcode app wrapper built from `safari-web-extension-converter`. All
  Safari extensions ship through the App Store; the old Safari Extensions
  Gallery closed in 2022.
- **Xcode is not installed on the build Mac** (only Command Line Tools), so
  the conversion step cannot run locally yet. One 2026-10-29 external review
  claimed App Store Connect can package Safari Web Extensions without Xcode;
  industry documentation as of May to September 2026 still describes the
  Xcode wrapper as required, so treat the no-Xcode claim as unverified and
  plan around installing Xcode.
- Each new browser multiplies the QA surface: the Safari build needs its own
  installed-extension acceptance pass in real Safari (popup lifecycle, event
  page wake on alarm, IndexedDB storage) before any submission. The synthetic
  DOM battery proves content-script logic only.

## Recommended sequencing

1. Decide the Apple Developer membership (cost decision, owner-level).
2. Install Xcode, run `xcrun safari-web-extension-converter` on a release
   tag, and record every API warning it emits.
3. Add `tools/build_safari.py` emitting the Safari manifest delta (reuse the
   Firefox event-page background; verify whether Safari accepts
   `data_collection_permissions`-style keys or needs them stripped).
4. Degrade the daily-review UI on iOS targets where `alarms` is absent;
   feature-detect at runtime, never assume.
5. macOS acceptance pass in real Safari, then TestFlight for iOS, before any
   App Store submission.

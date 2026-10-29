# Safari feasibility assessment

Date: 2026-10-29 (corrected same day against Apple's current documentation).
Scope: what it takes to ship fb-pfp on Safari for macOS and iOS. Every
claim carries its source; where sources conflict, the conflict is stated
instead of resolved by assumption.

## What works in our favor

- Safari Web Extensions are standard WebExtension packages: the same
  manifest, content script, popup and background files as Chrome and
  Firefox, wrapped in a containing app for distribution (Apple, "Safari Web
  Extensions", developer.apple.com, checked 2026-10-29).
- Safari supports Manifest V3 (Apple, WWDC26 session 216 "Create web
  extensions for Safari", 2026-10-27). Apple's own Xcode 26 template
  manifests use the `background.scripts` form with `type: "module"`, the
  same shape our Firefox build already emits, so the Safari manifest is a
  small delta on `tools/build_firefox.py`, not a new architecture.
- API surface is minimal: `alarms`, `runtime`, `storage`, `tabs`. All four
  exist in Safari Web Extensions on macOS (alarms since Safari 14, per MDN
  browser-compat data checked 2026-10-29).
- `chrome.storage.local.setAccessLevel` is already feature-detected as a
  Chromium-only hardening API, so its absence in Safari is a no-op.
- The content script uses standard DOM APIs only (canvas, createImageBitmap,
  DataTransfer, file inputs); nothing there is Chromium-specific.

## Distribution: what is and is not required

Correcting the earlier version of this document:

- **Paid Apple Developer Program membership (99 USD per year): required
  only for distribution** (App Store or TestFlight), not for local testing.
  Apple's Safari extensions page confirms the App Store Connect packager
  path: upload a ZIP of the extension and Apple converts and packages it
  for testing and App Store distribution (developer.apple.com/safari/
  extensions, checked 2026-10-29).
- **Xcode is no longer required for distribution packaging.** Since WWDC26
  (June 2026), the Safari Web Extension Packager in App Store Connect
  packages the extension without a Mac or Xcode; packaging runs on Xcode
  Cloud compute included in the membership (Apple, WWDC26 sessions 204 and
  216; developer.apple.com "Packaging a web extension for Safari", checked
  2026-10-29). The command-line `xcrun safari-web-extension-packager`
  (formerly `safari-web-extension-converter`) still exists for projects
  that need native code, a custom containing app, or local builds.
- **Xcode is still required for local macOS runtime testing.** Safari
  loads web extensions only from a containing app, and generating that app
  locally uses the packager CLI that ships with Xcode. Xcode itself is a
  free download; the paid membership is not needed to build, run unsigned,
  and test locally. Unsigned local testing: enable Develop > Allow
  Unsigned Extensions in Safari (resets when Safari quits), then enable
  the extension in Safari Settings > Extensions (Apple-documented flow,
  corroborated by multiple 2026 third-party guides).
- This Mac has Safari 27.2 on macOS 27.2 but only Command Line Tools; the
  Xcode install (free, owner action, roughly a 30 to 60 minute download)
  is the single blocker for local Safari runtime verification.

## Open items that must be tested, not assumed

- **Alarms API on iOS.** MDN browser-compat data lists no `safari_ios`
  support for any `alarms` member (checked 2026-10-29), while the 2026-10-29
  external review states Apple documents the Alarms API for iOS extensions.
  These conflict, and MDN's Safari iOS coverage for WebExtensions is known
  to lag. The daily-review schedule therefore cannot be claimed either
  supported or unsupported on iPhone and iPad until a real-device test.
  The safe build posture: feature-detect `alarms` at runtime and degrade
  the schedule UI where it is absent, so the manual Prepare and Change-now
  flows work everywhere regardless.
- **Scheduling reliability under iOS background execution**, even where the
  API exists, needs a device test; the OS decides when background work runs.
- **Manifest conversion warnings.** The packager prints unsupported
  manifest keys but never reads the JavaScript; expected flags for us are
  `minimum_chrome_version` and possibly the CSP object form. Record them
  on first conversion and audit by hand.

## Recommended sequencing

1. Install Xcode (free; owner decision). Run
   `xcrun safari-web-extension-packager --copy-resources` on a release tag
   and record every warning it emits.
2. Add `tools/build_safari.py` emitting the Safari manifest delta on the
   Firefox event-page background; strip `minimum_chrome_version`; verify
   what the packager says about `data_collection_permissions`-style keys.
3. Runtime-test in Safari on this Mac with Allow Unsigned Extensions:
   popup lifecycle, event page wake on alarm, IndexedDB storage, and the
   review flow against a local fixture.
4. Feature-detect `alarms` and degrade the schedule UI on iOS.
5. Only then decide on the 99 USD membership for App Store Connect
   packaging, TestFlight on a real iPhone, and App Store submission.

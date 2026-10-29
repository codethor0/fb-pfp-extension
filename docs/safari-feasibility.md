# Safari feasibility assessment

Date: 2026-10-29 (corrected twice same day against Apple's current
documentation; second correction adds the no-Xcode local load path).
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
- **Xcode is not required for local macOS runtime testing.** macOS Safari
  temporarily installs a web extension straight from its folder or a zip:
  Safari > Settings > Developer > Add Temporary Extension, with "Allow
  unsigned extensions" checked in the same tab (Apple, "Running your Safari
  web extension", developer.apple.com, checked 2026-10-29). The unsigned
  setting resets when Safari quits, and Safari removes temporary extensions
  after 24 hours or when it quits, so this is a development loop only, not
  a distribution channel. Xcode remains required only for iOS on-device
  testing, native code, or building a containing app locally.
- This Mac has Safari 27.2 on macOS 27.2, which supports the temporary
  folder load directly; local Safari runtime verification is unblocked.

## Local verification results (2026-10-29)

Tested the same day on this Mac, driving the documented Apple flow by UI
scripting (Safari Settings > Developer > Allow unsigned extensions, then
Add Temporary Extension with the staged folder):

- The temporary load works without Xcode, exactly as documented. Two
  password authentications were required: one to enable unsigned
  extensions, one implied by the flow on this macOS build.
- The extension appears in Settings > Extensions under "Temporary",
  enabled, version 0.4.3, with Uninstall / Show in Finder / Reload.
- The toolbar item installs ("fb-pfp Local Rotator") and the popup opens
  and renders fully, including the live photo count (0/20) read through
  storage, which proves the MV3 service worker and the storage API work
  in Safari.
- Not yet verified in Safari (need interactive passes): photo import into
  IndexedDB through the popup file picker, alarm creation and event-page
  wake, and the review flow on facebook.com after granting the website
  permission. The popup's controls are not exposed to macOS
  accessibility, so these steps are manual.
- Both developer settings reset when Safari quits, and Safari removes the
  temporary extension after 24 hours or on quit; no persistent change was
  left on the machine.

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

1. Build a Safari-manifest delta (`tools/build_safari.py`) on the Firefox
   event-page background; strip `minimum_chrome_version`; note anything
   else Safari-specific.
2. Runtime-test on this Mac with the temporary folder load: enable "Allow
   unsigned extensions", Add Temporary Extension, then verify popup
   lifecycle, event page wake on alarm, IndexedDB storage, and the review
   flow against a local fixture.
3. Feature-detect `alarms` and degrade the schedule UI on iOS.
4. Only then decide on the 99 USD membership for App Store Connect
   packaging, TestFlight on a real iPhone, and App Store submission. If
   the membership is taken, run the App Store Connect packager on a
   release tag and record every warning it emits; use the
   `xcrun safari-web-extension-packager` CLI only if native code or a
   custom containing app ever becomes necessary.

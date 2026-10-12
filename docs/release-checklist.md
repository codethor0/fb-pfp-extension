# Release checklist

A green unit-test suite does not establish compatibility with real Facebook or approval by a browser store.

## Automated gates

- [ ] `bash verify.sh --full` exits 0 and verifies the actual extension service worker using Playwright Chromium.
- [ ] `npm run check` passes on Node.js 20 and 22.
- [ ] `python tools/browser_smoke.py` passes with local Chromium.
- [ ] `python tools/popup_smoke.py` passes with local Chromium.
- [ ] The manifest remains limited to storage, alarms and the exact Facebook HTTPS origin.
- [ ] ZIPs contain no personal photos, screenshots, workspace paths, tokens or private logs.
- [ ] Store ZIP contains `manifest.json` at its archive root.
- [ ] Store listing screenshots and privacy URL accurately describe the tested build.
- [ ] Meta terms and Chrome Web Store policy have been independently reviewed for this functionality.
- [ ] `Change now` is always user-triggered and requires explicit confirmation.
- [ ] Scheduled review and `Prepare for review` never click Facebook Save.
- [ ] No dynamic remote JavaScript or externally connectable messaging is introduced.
- [ ] CI tests permissions and core logic before merge.

## Manual release gates

- [ ] Load unpacked successfully in Chrome on macOS.
- [ ] Load unpacked successfully in Brave on macOS.
- [ ] Import JPEG, PNG and WebP test images; verify correct metadata removal and removal controls.
- [ ] Check the real Facebook profile-picture cropper after Prepare for review.
- [ ] Verify the post composer remains untouched in each browser.
- [ ] Explicitly confirm Change now, verify the Save click, then check the resulting public profile picture.
- [ ] Disable Change now's confirmation and ensure the Publish button remains unavailable.
- [ ] Verify scheduled review, time selection and disabling the alarm.
- [ ] Confirm no duplicate extension installation or accidental schedule migration.
- [ ] Review store rules, Meta terms, privacy policy and source/archive contents before distribution.

## Publishing

- [ ] Keep the Python CLI repository and release tags unchanged.
- [ ] Integrate with the separate public extension repo only after a reviewed diff.
- [ ] Commits and pushes use the authenticated `codethor0` maintainer workflow, not development agents.
- [ ] Use a feature branch and reviewed pull request with green required checks.
- [ ] Source history, commit metadata and PR diffs are checked for personal details and build artifacts.
- [ ] Tag only after live tests pass and version numbers are aligned.
- [ ] Do not claim bug-free, production-ready or store-approved behavior without independent evidence.

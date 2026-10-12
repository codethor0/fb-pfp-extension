# Verification record

Date: 2026-10-11
Version: 0.2.1
Status: EXPERIMENTAL SOURCE CANDIDATE

## Checked in the build environment

- The Manifest V3 declares storage, alarms, and only `https://www.facebook.com/*` host access.
- Dependency-free unit tests and a static repository hygiene audit have been run.
- Offline Chromium content-script fixture verifies that review does not click Save.
- Offline Chromium content-script fixture verifies that explicit Change now clicks Save once and observes dialog closure.
- Offline Chromium fixture verifies that missing profile-dialog upload inputs stop without using the newsfeed composer.
- Offline Chromium popup fixture verifies local image import, removal, review, explicit publish confirmation and schedule controls.
- Package inspection excludes developer photos, workspace paths, credentials and private browser data.
- A one-command runner (`bash verify.sh --offline`) passed the static, 26 Node unit tests and both Chromium mock tests.
- The store ZIP generator checks that `manifest.json` is at the root of the ZIP.

## Not yet verified

- Full extension installation, service-worker lifecycle and alarms in a real Brave/Chrome browser on macOS.
- A new disposable-Playwright-Chromium MV3 extension lifecycle test (`bash verify.sh --full`) was created, but not run successfully in this build environment because a compatible browser could not be installed from the remote download service. Treat as UNVERIFIED, not passed.
- Live Facebook UI interactions, including the actual account-level final result.
- Handling of future Facebook A/B layout variations or language changes.
- Behavior after browser sleep, profile upgrades or service-worker termination.
- Browser store review or acceptance.

## Release rule

Install for local testing first. Do not claim successful unattended publishing or a bug-free production release. Change now must be deliberately enabled each time in the popup, and the user must confirm the result on Facebook.

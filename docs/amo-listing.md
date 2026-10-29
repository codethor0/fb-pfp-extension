# AMO listing draft

Paste-ready content for the addons.mozilla.org submission of fb-pfp.
Prepare by creating a Mozilla account at https://addons.mozilla.org/ then
open Developer Hub > Submit a new add-on. Upload
`dist/fb-pfp-extension-vX.Y.Z-firefox.zip` from the release page.

## Add-on id

`fb-pfp@codethor0.github.io` (baked into the built manifest; do not edit).

## Name

fb-pfp: Profile Picture Rotator

## Summary (max 250 characters)

Review or change your own Facebook profile picture using local photos you
choose. Runs entirely in your browser. No accounts, no servers, no tracking.

## Description

fb-pfp is a free, open-source browser extension that helps you review and
change the profile picture on your own Facebook account.

You keep a small library of photos inside the extension, stored locally in
your browser. Pick one, press Prepare for review, and fb-pfp opens
Facebook's own profile-picture dialog with your photo loaded so you can
check the crop before anything is published. Nothing is published
without an explicit second step: check the acknowledgment box and
press Change profile picture now, and only then does the extension click
Save inside the dialog. Placing a photo in the dialog hands it to
Facebook, exactly as a manual change would, even before you press Save.

What fb-pfp does:

- Stores up to 20 of your photos locally, converting them to privacy-safe
  JPEGs and stripping embedded camera metadata (EXIF/GPS).
- Compares the photo shown in Facebook's dialog against the photo you
  selected before any Save is attempted and refuses on any mismatch.
- Optionally rotates through your library without repeating photos.
- Can prepare a photo for your daily review at a time you choose; a
  scheduled run never clicks Save.
- Works on your own account in your own browser; the English-language
  Facebook interface is required.

What fb-pfp never does:

- No analytics, no ads, no telemetry, no third-party code.
- No server: photos never leave your browser except when they are handed
  to Facebook's own upload dialog, which is exactly what happens when you
  change a profile picture by hand.
- No credential handling. You log in to Facebook yourself.
- No posting, liking, messaging or any other action on your account.

Source code (MIT): https://github.com/codethor0/fb-pfp-extension

This independent project is not affiliated with, endorsed by, or sponsored
by Meta Platforms, Inc. Automating parts of a website may conflict with its
terms; use fb-pfp only on an account you own and at your own risk.

## Category

Social & Communication

## License

MIT (ships in the package as LICENSE)

## Privacy: data collection declaration

The manifest declares `data_collection_permissions: {required: ["none"]}`.
This is accurate: the extension collects and transmits no data to the
developer. Photos live in the browser's extension storage. The only network
destination the extension itself contacts is facebook.com, as part of the
profile-picture flow the user explicitly starts.

## Reviewer notes

- The add-on is built from the public repository above; the submitted zip
  is produced by `python3 tools/build_firefox.py` from an unmodified
  checkout of the tagged release.
- The only host permission is `https://www.facebook.com/*`; the only
  permissions are `storage` and `alarms`.
- Automatic Save is gated behind an in-popup acknowledgment checkbox plus a
  dedicated button; a separate Prepare mode stages the photo without any
  Save. The content script verifies the staged preview against the selected
  image pixels before Save and refuses on any mismatch.
- LinkedIn and X adapters exist in the source as disabled contracts; only
  the Facebook adapter is enabled, and host permissions are not broadened.

## Submission checklist (updated 2026-10-29)

Everything below is verified except the steps marked (human), which need
Thor's Mozilla account and click:

1. Build the package from the tagged release:
   `python3 tools/build_firefox.py` (self-checks pass).
2. Confirm the built manifest: gecko id `fb-pfp@codethor0.github.io`,
   `strict_min_version` 140.0, `data_collection_permissions: {required: ["none"]}`,
   event-page module background, permissions `storage` + `alarms` only.
   Verified on the staged candidate (sha256
   558a0cb79ea1c7ef2c11292a9854e5c348a9455517572b99e66ad12af6a47924).
3. (human) Create a Mozilla account at https://addons.mozilla.org/ if none
   exists, enable two-factor authentication, and open Developer Hub.
4. (human) Submit a new add-on, upload the zip from the release tag, and
   paste Name / Summary / Description / Category / License from above.
5. (human) Confirm the data-collection declaration: no data collected.
6. (human) Paste the reviewer notes verbatim.
7. Wait for review; respond in the reviewer thread if questions come back.

Version rule: submit a build whose version tag matches the CWS train. The
staged 0.4.3 candidate carries post-0.4.3 code, so submit it only after the
CWS 0.4.3 verdict lands and the tree is tagged 0.4.4; then rebuild from that
tag and update the version strings above before uploading.

# Changelog

## [0.2.2] - 2026-10-12

- A Save click that Facebook never confirms (the dialog cancels, errors, or never settles) now counts the photo as used instead of failing the run and retrying the same photo immediately. The popup reports the unconfirmed outcome honestly and the rotation advances.
- The content script now rejects messages not sent by this extension, so another extension id cannot drive the profile-picture dialog.
- An upload file input must declare image-only accept types. An input without an accept attribute is never used.
- Rotation settings updates are serialized, so overlapping runs cannot lose rotation state.
- A scheduled daily review opens the Facebook tab in the background. Tabs opened by your own clicks stay in the foreground.
- Documented that runs intentionally leave the Facebook tab open for your inspection.
- Added regressions for the unconfirmed Save outcome, unknown message senders and accept-less file inputs. The full battery now passes 60 checks from a clean clone.

## [0.2.1] - 2026-10-12

- Verified the packaged build against the owner's live Facebook account: Prepare for review opened the real profile-picture dialog with the selected photo, left the composer untouched, and the dialog was dismissed without changes.
- Submitted the Chrome Web Store listing for review with automatic publication after approval. Synced the public repository, privacy policy, listing and staged package.
- Repaired the test harness: strip every ES module export when inlining images.mjs, define the chrome stub before use, and wait for a render-settled popup state.
- Added repository badges, a Support section and GitHub Sponsors funding metadata.
- Added selected-image preview checks, guarded upload-input attribution, stable Save acknowledgement, and cancellation handling.
- Expanded content regressions and actual Chrome/Brave lifecycle checks, including persistent photo bytes and scheduled review.

- Added a one-command verification runner, safe Makefile shortcuts and real-extension synthetic Chromium lifecycle test.
- Added store submission preparation, privacy and listing guidance.
- Added reproducible, validated source, sideload and store-root ZIP packaging.
- Fixed the lifecycle test: it now runs under the extension content-security policy and serves its own local HTTPS fixture for www.facebook.com, with every other host unresolvable.
- Fixed the upload into Facebook's profile-picture dialog: the dialog is looked up again on every check (Facebook opens it empty and can replace it while its contents load), the file input is taken from the dialog or from the input that the dialog's own Upload photo button makes Facebook click (never a video or post-composer input), and a failure reports element counts only. Pressing an avatar that is an SVG no longer throws.
- Privacy policy now states that the optional daily review also runs without a click.
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

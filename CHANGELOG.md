# Changelog

## [Unreleased]

- No-repeat rotation no longer opens a new round with the photo that was just saved. When the last unused photo is saved, the round resets but keeps that photo marked as used, so with 2 or more photos the next pick always differs (before, it repeated with probability 1/N, for example 34% with three photos). A single photo still repeats, as it must.

## [0.2.5] - 2026-10-15

- Scheduled daily reviews reuse the Facebook tab a previous scheduled run left open instead of opening a new one every day. The tab qualifies only while it still shows an allowed Facebook page and is not focused. After a failed scheduled run the tab closes itself only when nothing was staged into the dialog and it is not the active tab; successful runs keep and remember the tab. Runs started from the popup never close or reuse tabs.
- The profile-picture dialog is matched by accessible name first. A dialog named something else, for example "Create post", whose body text mentions profile pictures is no longer mistaken for the target dialog, and a named profile-picture dialog wins over an unnamed lookalike.
- A previously verified preview image must still be visible to gate Save; a hidden or superseded image no longer authorizes an automatic Save.
- The popup status line is height-capped and scrolls, so many failed imports can no longer grow over the controls.
- Added regressions for all four fixes. The full battery now passes 66 checks from a clean clone.


## [0.2.4] - 2026-10-13

Security hardening pass over the full attack surface; no behavior change for normal use.

- The extension pages CSP now sets `object-src 'none'` (was `'self'`). No object or embed content is used anywhere.
- Cross-origin preview re-fetches in the content script are size-capped (Content-Length and decoded body, 32 MiB), so a hostile or broken page cannot push an unbounded image into `createImageBitmap`.
- IndexedDB photo records are validated on every read; a corrupted or tampered library degrades gracefully instead of bricking the popup or the worker.
- Fixed the popup version badge, which still showed 0.2.2.
- The release audit now pins the popup badge to the manifest version, requires the strict CSP, and tripwires the preview size cap and read-path record validation.
- Added hostile-input regressions: userinfo and lookalike-host URL tricks, prototype-pollution shapes in settings and storage, unbounded `usedIds` and `lastResult`, NaN random sources, duplicate ids, malformed photo records, and multi-URL error redaction.


## [0.2.3] - 2026-10-12

- Fixed the known CDN verification limitation from 0.2.2: Facebook serves the staged preview from its own CDN, which taints canvas sampling and made the pixel-match gate decline every automatic Save. The content script now re-fetches a cross-origin preview untainted (the CDN permits reads from www.facebook.com) and verifies those bytes before Save. Same-origin, blob and data previews are still sampled directly, and an unchanged strict tolerance applies.
- Automatic Save now works end to end on the live cropper: the staged photo is verified against the uploaded bytes and Save proceeds. Any real mismatch, dialog error, or busy state still stops fail-safe with manual Save guidance.
- Added regression coverage for both sides of the cross-origin case: a tainted CDN preview with matching pixels is verified and reaches Save, and a CDN preview with different pixels never reaches Save. The full battery now passes 63 checks from a clean clone.

## [0.2.2] - 2026-10-12

- A Save click that Facebook never confirms (the dialog cancels, errors, or never settles) now counts the photo as used instead of failing the run and retrying the same photo immediately. The popup reports the unconfirmed outcome honestly and the rotation advances.
- The content script now rejects messages not sent by this extension, so another extension id cannot drive the profile-picture dialog.
- An upload file input must declare image-only accept types. An input without an accept attribute is never used.
- Rotation settings updates are serialized, so overlapping runs cannot lose rotation state.
- A scheduled daily review opens the Facebook tab in the background. Tabs opened by your own clicks stay in the foreground.
- Documented that runs intentionally leave the Facebook tab open for your inspection.
- Added regressions for the unconfirmed Save outcome, unknown message senders and accept-less file inputs. The full battery now passes 61 checks from a clean clone.
- Fixed a live-site false negative: Facebook clears the file input right after reading it, which made every successful upload report "Facebook did not receive the selected image file". Acceptance is now proven only by the preview check that gates Save. Verified against the owner's live account with the 0.2.2 build.
- Known limitation: on the live cropper Facebook re-encodes the staged photo and serves it from its CDN, so the pixel-match gate can decline automatic Save conservatively. The run stops fail-safe with manual Save guidance; Prepare for review is unaffected.
- Added `tools/store_resubmit.py` to replace a staged store package and resubmit for review through the maintainer's own signed-in browser once a pending review unlocks the package tab.
- PNG dimensions are now read from the IHDR chunk before decoding, and a 64 MP pixel budget backstops every decoded image, closing the decompression-bomb gap in photo import.

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

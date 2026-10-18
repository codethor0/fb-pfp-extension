# Changelog

## [Unreleased]

- The offline DOM battery now exercises the content script's fail-closed site guards directly, instead of stripping `validatePage()` out of the source under test. A `guard_source` build keeps the guards while replacing `location.protocol`, `hostname` and `pathname` with injectable fakes, and a `run_guard` helper drives seven assertions: LinkedIn and X refuse while their adapters stay disabled, an unknown host is named in the error, `http:` is refused, the login wall is named, a real profile path passes through to the flow, and a non-profile path under an allowed host is refused. Verified: 68 PASS on Chromium, 69 PASS on Firefox, 0 failures on both.
- `tools/browser_smoke.py --browser firefox` now runs the full DOM battery on macOS 27 instead of reporting SKIP. Playwright's bundled Firefox resolves the TCC-protected `~/Library/Application Support/Firefox` app-data dir and was denied access (microsoft/playwright#42768). When a plain launch fails, the harness stages a one-time copy of the playwright build in the user cache, points it at an identical `application.ini` with a distinct Name/Vendor so it resolves a non-protected app-data dir, and relaunches it through a small argument-reordering launcher (`-app` must be the first argument, which playwright cannot express itself). The copy is keyed by the playwright build number and is never shipped. Verified: 62 PASS, 0 failures on Firefox 155.0; the Chromium pass is unchanged and stays the hard gate.

## [0.4.2] - 2026-10-16

- A Save click that Facebook never confirms is no longer reported as acknowledged. The on-page notice and the popup status both said "Save acknowledged" for an unconfirmed Save (cancel, error or a dialog that never settled), even though the rotation state and the stored result were already correct. Both now say the Save was clicked but not confirmed. Regressions cover the popup and the page notice for every unconfirmed case.
- A transient failure to fetch a cross-origin preview image no longer poisons verification for the rest of the wait. The untainted re-fetch is retried up to two times with a short delay; a preview that keeps failing still blocks Save, and mismatched pixels still never pass.

## [0.4.1] - 2026-10-15

- The Firefox add-on id is now `fb-pfp@codethor0.github.io`, matching the maintainer's GitHub namespace. AMO add-on ids are effectively permanent, so this was corrected before the first submission; the previous id pointed at a github.io subdomain the maintainer does not control.
- Added docs/amo-listing.md: a paste-ready AMO listing draft (name, summary, description, category, license, privacy notes and reviewer notes) so submission is a copy-paste once the maintainer creates a Mozilla account.

## [0.4.0] - 2026-10-15

- Added the site-adapter architecture: site-specific labels and page guards now live in per-site adapters while the scoped upload, untainted preview verification and the gated Save flow stay shared core. Facebook remains the only enabled adapter.
- Added contract-only adapters for LinkedIn and X. Both ship disabled: their logged-in DOMs must be probed on real accounts before any selector ships, and both sites restrict automation. Enabling an adapter is a deliberate change, never a guess, and host permissions are not broadened until then.
- The page guard now names the unsupported host instead of assuming Facebook, so future adapters fail closed with a clear message.

## [0.3.1] - 2026-10-15

- The Firefox manifest now declares `data_collection_permissions: {required: ["none"]}`, which addons.mozilla.org has required for every new add-on since 2025-11-03. Without this key the upload is rejected at validation time.
- The Firefox background now points `background.scripts` directly at `src/background.mjs` with `type: "module"`; the `src/background-firefox.js` wrapper from 0.3.0 is removed. Firefox honors module background scripts, so the indirection served no purpose.
- The Firefox floor is now desktop 140.0 and Android 142.0, the versions where Firefox's built-in data consent prompt exists; the built package also declares `gecko_android`.
- The release audit tripwires these Firefox invariants: the AMO data declaration must exist, the background path must come from the Chromium service worker entry, and the removed wrapper must stay removed.

## [0.3.0] - 2026-10-15

- No-repeat rotation no longer opens a new round with the photo that was just saved. When the last unused photo is saved, the round resets but keeps that photo marked as used, so with 2 or more photos the next pick always differs (before, it repeated with probability 1/N, for example 34% with three photos). A single photo still repeats, as it must.
- The popup now reflects the stored schedule time after saving preferences instead of rendering an empty time field when the stored default differed from the control's initial value.
- Added Firefox build support: `python3 tools/build_firefox.py` emits an unsigned Firefox package from the same source. Firefox runs the background as an event page module through a thin wrapper, and the storage access-level call (a Chromium-only API) is now feature-detected. The package installs temporarily from `about:debugging`; an AMO listing is pending.
- Honest CI note: the dual-engine lifecycle pass runs the Firefox engine when available and reports SKIP on macOS hosts where the sandboxed engine launch is blocked by system privacy controls. Chromium remains the hard gate; nothing is claimed green from a skipped engine.

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

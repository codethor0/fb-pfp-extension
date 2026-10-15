# Firefox

The Chromium manifest is the source of truth. Firefox runs Manifest V3
background code as an event page (`background.scripts`) instead of a service
worker, and AMO requires a gecko id plus a data collection declaration, so a
small build step writes a transformed manifest for the Firefox package and
leaves the Chrome package untouched.

## Build

```bash
python3 tools/build_firefox.py            # writes dist/fb-pfp-extension-vX.Y.Z-firefox.zip
```

## Install locally

The zip is unsigned by design. Open `about:debugging` in Firefox, select
**This Firefox**, then **Load Temporary Add-on**, and pick the `manifest.json`
from the extracted zip. A temporary add-on lasts until Firefox restarts.
Sign in to Facebook normally in the same browser, then follow the review-first
steps from the main README: press **Prepare for review** and check the dialog
before ever pressing **Change profile picture now**.

## What differs from Chromium

- `background.scripts` points at the same `src/background.mjs` the Chromium
  service worker uses, loaded with `type: "module"`. No wrapper, no duplicated
  logic.
- `browser_specific_settings.gecko` carries the add-on id, a desktop floor of
  Firefox 140.0, and `data_collection_permissions: {required: ["none"]}`,
  which AMO has required for every new add-on since 2025-11-03. This extension
  collects nothing, so the declaration is `none`.
- `gecko_android` sets an Android floor of 142.0, matching the version where
  Firefox's built-in data consent prompt exists.
- `storage.local.setAccessLevel` is a Chromium-only API and is feature-detected
  at startup; Firefox skips it.

## Status

Verified live on Firefox (2026-10-15, fb-pfp 0.4.0): the temporary add-on
installed into a real Firefox profile, the popup imported a JPEG through the
file input, and a Prepare run opened the maintainer's real profile, staged
the photo into Facebook's "Choose profile picture" dialog, verified the
preview, and stopped before Save. The Firefox build is no longer
experimental for the review flow. The Change now path (automatic Save) has
not been exercised on Firefox and stays gated behind the same explicit
confirmation as everywhere else.

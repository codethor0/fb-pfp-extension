# Firefox

The Chrome manifest is the source of truth. Firefox needs a different background
declaration, an add-on id and a data-collection declaration, so a small script
generates a Firefox copy and leaves the Chrome package alone.

## Build and try it

```bash
npm run build:firefox                      # writes dist/firefox
npx web-ext lint --source-dir dist/firefox
npx web-ext run --source-dir dist/firefox --target firefox-desktop
```

`web-ext run` loads the extension into a temporary Firefox profile. Use it
with a test Facebook account first, and press Prepare, not Change now.

## What differs from Chrome

- The background script runs as an event page (`background.scripts`), not a service worker.
- The manifest carries `browser_specific_settings.gecko` with the add-on id, a
  minimum Firefox version of 140 (142 on Android), and `data_collection_permissions: none`.
- `storage.local.setAccessLevel` is used only where the browser provides it.
- Host permission for `https://www.facebook.com/*` is shown in Firefox's install
  prompt. If you removed it under the add-on's Permissions tab, grant it again.

## Status

The build script, the manifest transform and the startup guard are covered by
offline tests. The upload hand-off into Facebook's dialog has not yet been
verified on Firefox. Treat the Firefox build as experimental until
`web-ext run` completes a Prepare on a real profile page.

# Roadmap

Where the project is going and why. Items ship when they are verified, not before.

## Now

- Chrome Web Store review of the current build. The staged package is
  replaced automatically the moment the package tab unlocks.
- Distribution: launch posts, demo GIF, store screenshots. Assets live in
  `docs/`.

## Next

- **Firefox port.** The extension uses MV3 modules, IndexedDB and alarms,
  all supported by Firefox. The port is packaging and test coverage, not a
  rewrite.

## After that

- **More sites through the adapter architecture.** The content script is
  already split into shared core (scoped upload, untainted preview
  verification, gated Save) and per-site adapters. Facebook is the only
  enabled adapter. LinkedIn and X adapters exist in code but ship disabled,
  because their logged-in DOMs must be probed on real accounts before any
  selector ships and both platforms restrict automation. An adapter is
  enabled only after it passes the same fail-safe standard Facebook meets:
  no blind clicks, verification before Save, manual-confirm default on
  restrictive platforms.

## Never

- Accounts, servers, analytics, or ads.
- Shipping a selector we have not verified against the live site.
- Clicking Save without the explicit confirmation path.

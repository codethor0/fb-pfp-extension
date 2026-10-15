# Roadmap

Where the project is going and why. Items ship when they are verified, not before.

## Now

- Chrome Web Store review of 0.2.5. A watcher checks the review outcome and
  records it for the maintainer.
- Firefox build support shipped in 0.3.0 (event-page module background,
  `tools/build_firefox.py`). An AMO listing is pending maintainer keys.
- Distribution: launch posts, demo GIF, store screenshots. Assets live in
  `docs/`.

## Next

- **Automated Gecko engine coverage.** The offline DOM battery accepts
  `--browser firefox`, but macOS 27 TCC blocks any sandboxed Firefox launch
  (see microsoft/playwright#42768), so the harness reports SKIP there. On
  machines where Firefox launches normally, the pass runs the full battery.
  The Chromium pass remains the hard gate everywhere.

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

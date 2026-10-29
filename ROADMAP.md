# Roadmap

Where the project is going and why. Items ship when they are verified, not before.

## Now

- Chrome Web Store: 0.2.5 approved and live; 0.4.2 submitted and pending
  review. A watcher checks the review outcome and records it for the
  maintainer.
- Firefox build support shipped in 0.3.x (event-page module background,
  `tools/build_firefox.py`, AMO data declaration). An AMO listing is pending
  maintainer keys.
- Site-adapter architecture shipped in 0.4.0: shared core (scoped upload,
  untainted preview verification, gated Save) with per-site adapters. Facebook
  is the only enabled adapter. LinkedIn and X adapters exist as enforced
  contracts and ship disabled.
- Gecko battery coverage: on macOS 27, `--browser firefox` now relaunches
  playwright's Firefox under a rebranded app-data dir instead of reporting
  SKIP (upstream: microsoft/playwright#42768). The full battery passes on
  Firefox 155.0; the Chromium pass remains the hard gate.
- Distribution: launch posts, demo GIF, store screenshots. Assets live in
  `docs/`.

## After that

- **Local export workflow for LinkedIn.** LinkedIn's terms prohibit
  third-party automation, so the DOM adapter stays disabled
  (`uploadAction: null`) permanently; the adapter spec is kept as
  historical research. The supported feature prepares a metadata-free
  square JPEG locally and downloads it for the user to upload through
  LinkedIn's own interface. Design: docs/linkedin-local-workflow.md.
- **Safari runtime verification on this Mac.** macOS Safari loads the
  extension folder temporarily without Xcode (Add Temporary Extension);
  assess docs/safari-feasibility.md before any distribution decision.
- X remains a contract entry only, disabled, until its terms permit a
  maintainable path.

## Never

- Accounts, servers, analytics, or ads.
- Shipping a selector we have not verified against the live site.
- Clicking Save without the explicit confirmation path.

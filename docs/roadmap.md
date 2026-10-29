# Expansion roadmap

How fb-pfp grows beyond Facebook without giving up the rules it was built
on: probe before code, fail closed, review-first, local only, no telemetry.

## Platform adapters

Each new site follows the same gate the LinkedIn adapter is going through:

1. Read-only probe of the logged-in DOM on the maintainer's own account,
   English UI, paced like a human. Nothing uploaded, staged or saved.
2. Spec document: allowed anchors (ARIA labels, heading text, roles),
   forbidden anchors (hashed classes, positional indexes, CDN URL shapes),
   the stage-by-stage flow, fail-closed rules, open items.
3. Offline half: adapter config plus synthetic DOM battery fixtures on both
   engines, shipping disabled. Negative fixtures mirror the site's risk
   profile (danger labels, decoys, ambiguous candidates).
4. Live dry-run with the maintainer at the screen: stage a real photo into
   the site's editor, stop before Save, screenshot-verified.
5. Deliberate enablement in a release: host permissions broadened in the
   same release, called out in the changelog, release audit tripwires the
   change.

Order of attack, by demand and by DOM stability:

- LinkedIn: offline half done; live probe items are listed in
  docs/linkedin-adapter-spec.md (viewer action labels, file input mount
  point, cropper structure, post-save signal).
- Instagram: research item. instagram.com web profile editing exists, but
  the photo editor's DOM is unprobed. Needs the same probe before any
  selector is written.
- X: contract entry only. X restricts automation aggressively; revisit only
  if the adapter architecture proves itself on LinkedIn.

## Browser matrix

- Chromium: shipped, Chrome Web Store.
- Firefox: build tooling exists (tools/build_firefox.py); publishing needs a
  Mozilla account and an AMO listing, following docs/amo-listing.md. The
  0.4.3-content candidate package is staged at
  store-release/fb-pfp-extension-v0.4.3-firefox-candidate.zip (sha256
  558a0cb79ea1c7ef2c11292a9854e5c348a9455517572b99e66ad12af6a47924),
  built from main after PR #15. Submit it only after the CWS 0.4.3 verdict
  lands and the tree is tagged 0.4.4, so the version number means the same
  thing on every store.
- Edge: the Chromium package installs as-is; the Microsoft Partner Center
  listing is a paperwork step, not a code step. Verified 2026-10-29 on real
  Microsoft Edge 156.0.4314.50 (macOS, arm64): the full DOM battery passes,
  80 PASS / 0 FAIL. Edge cannot be playwright-launched directly: its data-dir
  name is compiled into the brand and macOS TCC denies a CLI-spawned process
  the protected default dir, so the harness connects over CDP instead
  (launch headless via `open -na "Microsoft Edge" --args --headless=new
  --remote-debugging-port=9223 about:blank`, then run the battery with
  `CDP_URL=http://localhost:9223`). The remaining Edge work is a Partner
  Center submission and an installed-extension acceptance pass in real Edge.
- Safari: assessed in docs/safari-feasibility.md (2026-10-29). Feasible on
  macOS with the Firefox-style event-page background, but distribution needs
  the Apple Developer Program (99 USD per year), an Xcode wrapper, and an
  installed-extension acceptance pass. iOS additionally lacks the `alarms`
  API, so the daily-review schedule cannot work there. Xcode is not
  installed on the build Mac yet; that and the membership are the two
  owner-level decisions blocking this lane.

## Funding

The extension stays local-only and MIT. That rules out in-app purchases of
core features and any hosted sync. Funding paths that do not compromise the
model:

- GitHub Sponsors on codethor0/fb-pfp-extension: the lowest-friction option,
  sits next to the code, needs a payout method.
- Buy Me a Coffee or ko-fi: a link in the README, the store listing and the
  popup footer. No account needed to give.
- Open Collective: worth it only if contributor count grows past a handful;
  overhead is not justified yet.

Anything stronger (paid tiers, hosted services) contradicts the privacy
posture that makes the project worth funding. Donations first, revisit only
with a user base asking for more.

## Release discipline

Every adapter enablement is a minor version with a full battery run on both
engines, the static audit, and a changelog entry naming the new host
permissions. No adapter ships enabled from a fixture alone; the live
dry-run is the gate.

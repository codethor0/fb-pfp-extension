# Expansion roadmap

How fb-pfp grows beyond Facebook without giving up the rules it was built
on: probe before code, fail closed, review-first, local only, no telemetry.

## Platform adapters

Each new site follows the same gate, and the gate starts with permission,
not selectors: a platform whose terms prohibit automation never gets a
live adapter at all. Where automation is permitted (Facebook today), the
sequence is:

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

- LinkedIn: automation dead end by policy; the adapter stays disabled
  (`uploadAction: null`) forever. The supported path is the local
  photo preparation and export workflow in
  docs/linkedin-local-workflow.md; the probe-era spec in
  docs/linkedin-adapter-spec.md is kept as historical research only.
- Instagram: research item. instagram.com web profile editing exists, but
  the photo editor's DOM is unprobed. Needs the same probe before any
  selector is written.
- X: contract entry only. X restricts automation aggressively; revisit
  only if its terms permit and a maintainable, permitted path exists.

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
  `CDP_URL=http://localhost:9223`). Installed-extension acceptance also
  passes on real Edge (tools/edge_acceptance.py, 2026-10-29, 11 checks):
  service worker install, settings round-trip, image import into IndexedDB,
  daily-review alarm creation, storage flushed to disk, fresh-session boot,
  and the review flow end to end against a mapped fixture, with Save
  untouched. Two checks stay manual: cross-restart library persistence
  (Edge headless uses a throwaway scoped profile and Edge 156 blocks CDP on
  the default profile) and any live-Facebook verification. The remaining
  Edge work is a Partner Center submission and those headed manual passes.
- Safari: corrected against Apple's current documentation in
  docs/safari-feasibility.md (2026-10-29). Xcode is no longer needed for
  distribution packaging (the App Store Connect Safari Web Extension
  Packager, WWDC26, packages a ZIP without a Mac) and is not needed for
  local macOS testing either (Safari loads the extension folder or zip
  temporarily via Settings > Developer > Add Temporary Extension). A paid
  membership is still required only for distribution through App Store
  Connect. The iOS Alarms API conflict (MDN: unsupported; external review:
  Apple documents it) stays open until a real-device test; the build will
  feature-detect alarms and degrade the schedule UI rather than assume.
  Local Safari runtime verification is unblocked on the build Mac.

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

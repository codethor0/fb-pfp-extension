# LinkedIn adapter specification

> Historical research, 2026-10-17 probe era. Not an active implementation
> plan: LinkedIn's user agreement prohibits third-party automation, the
> adapter stays permanently disabled behind `enabled: false` with
> `uploadAction: null`, and no live probe, staged upload, or selector
> verification will ever run against LinkedIn. The supported path is the
> local preparation and export workflow in
> docs/linkedin-local-workflow.md. This document is kept so the offline
> battery fixtures retain their design rationale.

Status at freeze: offline half implemented behind `enabled: false`. The avatar finder,
dialog identity check, scoped danger-label guard and profile-path guard run in
the synthetic DOM battery on both engines. The guard rejects destructive or
ambiguous action candidates rather than the whole dialog, so verified upload
and Save controls beside delete, remove or frames controls remain usable. The
upload control labels remain open probe items; `uploadAction` stays `null`, so
the adapter stages nothing.
No selector in this document is live code, and none may ship until each one
is verified against the live site on a real account, the same standard the
Facebook adapter meets.

## Probe evidence

Collected read-only on the maintainer's own logged-in profile
(2026-10-17, Brave, English UI). Nothing was uploaded, staged, saved or
deleted during the probe.

- Own profile URL pattern: `/in/{slug}/?isSelfProfile=true`. The flag is a
  useful precondition check.
- Top-card profile photo: an `img` with empty `alt`, roughly 100 to 130 CSS
  px, whose `src` is a `media.licdn.com` URL containing the path segment
  `profile-displayphoto`. The cover photo is a separate
  `img[alt="Cover photo"]` and must never be treated as the avatar.
- Clicking the top-card photo opens a viewer modal:
  - Heading: `h2` with text "Profile photo".
  - Large photo: `img[alt="Profile image"]`.
  - Close control: `button[aria-label="Dismiss"]`.
  - Visibility control with text "Anyone".
  - A bottom action cluster of icon buttons (observed visually: edit,
    update/upload, frames, delete). Exact aria-labels and the icon
    identifiers were not captured and are an open item below.
- No `input[type="file"]` exists anywhere on the profile page or in the
  viewer until the upload flow is entered.
- Class names across the top card and modal are short hashed strings
  (for example `i0lml4 i0lml3 ...`). They are build artifacts, not stable
  selectors, and must not be used.

## Selector strategy

Anchors allowed, in priority order:

1. ARIA labels on buttons (`button[aria-label="..."]`).
2. Heading text for dialog identity ("Profile photo").
3. `img[alt="Profile image"]` for the staged preview inside the dialog.
4. Role attributes (`role="dialog"`, `role="menu"`).

Anchors forbidden: hashed class names, positional indexes, `media.licdn.com`
URL shapes for DOM selection (CDN shapes are fine as a pixel-source hint
only, never to find elements).

## Proposed flow (to verify stage by stage)

1. Navigate to the own profile. Fail closed unless `isSelfProfile=true`.
2. Click the top-card photo (the 100 to 130 px `img` under the cover, not
   `img[alt="Cover photo"]`). Expect the "Profile photo" viewer modal.
3. Click the update/upload action in the modal. Expect a file input to
   mount (location: open item).
4. Set the local file on that input only. Never click anything labeled
   delete, remove, or frames.
5. Verify the staged preview by pixels, the same untainted re-fetch
   approach the Facebook core uses: the preview image must decode to bytes
   matching the local file within tolerance, and the Save control must be
   enabled.
6. Save is gated. On LinkedIn the default is manual-confirm even after the
   adapter ships: the extension stages and verifies, the user clicks Save
   on the site. Automatic Save is a separate deliberate decision per the
   roadmap.

## Fail-closed rules (additive to the shared core)

- No blind clicks: every stage verifies the expected dialog/heading exists
  before acting.
- Any `button` whose label matches delete/remove/trash/frames ends the run
  immediately.
- If the viewer modal does not contain both the "Profile photo" heading and
  `img[alt="Profile image"]`, stop.
- If `isSelfProfile` is not present, stop. The adapter never touches a
  profile that is not the logged-in user's own.
- Host permissions for linkedin.com are broadened only in the release that
  enables the adapter; the release audit tripwires the change.

## Risks

- DOM churn: LinkedIn ships frequent layout changes; ARIA/text anchors are
  more durable than classes but still need the live-probe gate before each
  enablement.
- Automation detection: probing and testing must be paced like a human,
  minimal page loads, no rapid retries.
- The "Frames" feature can intercept the photo element; the delete and
  frames controls sit adjacent to the upload control, so label-strict
  targeting matters.
- Layout A/B variants may present a different entry (for example an
  "Add photo" overlay on hover instead of the viewer). The spec covers the
  viewer path only; a variant path is a new probe, not an assumption.

## Open items for the next live probe

(Frozen. The sections below describe what a next probe would have covered;
per the header, no next probe will happen.)

1. Aria-labels and icon identifiers of the viewer's action buttons
   (update/upload especially).
2. Where `input[type="file"]` mounts: viewer, a follow-up dialog, or a
   cropper step, and its `accept` attribute.
3. Cropper structure: canvas vs img preview, zoom controls, and the Save
   button's label and enabled-state semantics.
4. Whether a confirmation step appears after Save.
5. Post-save verification signal: avatar `src` change on profile reload,
   and how long CDN cache delays it.

## Verification plan before enablement

- Offline: the synthetic DOM battery gains LinkedIn fixtures mirroring the
  probed structure, run under both engines, with the same negative cases
  Facebook runs (ambiguous inputs, duplicate avatars, spoofed previews,
  missing dialog).
- Live: a dry-run on the maintainer's account stages a real photo into the
  cropper and stops before Save, screenshot-verified, exactly like the
  Facebook Prepare verification. Only after that does the adapter get
  enabled in a release, with host permissions broadened deliberately and
  the change called out in the release notes.

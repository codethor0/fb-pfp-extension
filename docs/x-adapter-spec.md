# X adapter specification

Status: spec only. The adapter ships disabled. No selector in this document
is live code, and none may ship until each one is verified against the live
site on a real account, the same standard the Facebook adapter meets.

## Probe evidence

Collected read-only on the maintainer's own logged-in account
(2026-10-17, Brave, English UI). The edit-profile dialog was opened and
inspected. No file was set on any input, nothing was saved.

- Own profile resolves through the left nav
  (`a[data-testid="AppTabBar_Profile_Link"]`).
- Profile header avatar: `img[alt="Opens profile photo"]`, roughly 130 CSS
  px, `src` from `pbs.twimg.com/.../profile_images/...`.
- Profile edit entry: `a[data-testid="editProfileButton"]` with text "Edit
  profile".
- Edit dialog heading: "Edit profile".
- Avatar edit trigger: `button[aria-label="Add avatar photo"]`.
- Banner edit trigger: `button[aria-label="Add banner photo"]` sits in the
  same dialog. It must never be targeted; see fail-closed rules.
- File inputs: `input[type="file"][data-testid="fileInput"]`, two in the
  dialog, both `accept="image/jpeg,image/png,image/webp"`, one in the
  banner region and one in the avatar region. Trigger-to-input pairing must
  be verified before enablement.
- Save control: `Profile_Save_Button` (text "Save"), disabled state
  exposed through `aria-disabled`.
- Avatar container in the dialog: `[data-testid="UserAvatar-Container-{handle}"]`.

X surfaces `data-testid` attributes widely. They are the conventional
anchor for X and are used here, with the same live-probe gate as every
other selector.

## Selector strategy

Anchors allowed, in priority order:

1. `data-testid` attributes (`editProfileButton`, `fileInput`,
   `Profile_Save_Button`, `UserAvatar-Container-{handle}`).
2. ARIA labels (`button[aria-label="Add avatar photo"]`).

Anchors forbidden: hashed or generated class names, positional indexes,
twimg URL shapes for DOM selection (CDN shapes are fine as a pixel-source
hint only, never to find elements).

## Proposed flow (to verify stage by stage)

1. Navigate to the own profile through the left nav link.
2. Click `editProfileButton`. Expect the "Edit profile" dialog.
3. Click only `button[aria-label="Add avatar photo"]`. Expect the avatar
   file input to become the active input.
4. Set the local file on that input only. Verify the input's `accept`
   covers the file type first.
5. Verify the staged preview by pixels, the same untainted re-fetch
   approach the Facebook core uses: the preview image must decode to bytes
   matching the local file within tolerance, and Save must be enabled.
6. Save is gated. On X the default is manual-confirm even after the
   adapter ships: the extension stages and verifies, the user clicks Save
   on the site. Automatic Save is a separate deliberate decision per the
   roadmap.

## Fail-closed rules (additive to the shared core)

- No blind clicks: every stage verifies the expected dialog/heading exists
  before acting.
- The dialog must contain exactly one avatar trigger labeled "Add avatar
  photo". Zero, or more than one, ends the run.
- Any element labeled banner, header, or cover ends the run. The banner
  input accepts the same image types as the avatar input, so label-strict
  targeting is the only safe discriminator.
- If the dialog cannot be confirmed as the own profile editor (heading
  "Edit profile" plus the own-handle avatar container), stop.
- Host permissions for x.com are broadened only in the release that
  enables the adapter; the release audit tripwires the change.

## Risks

- `data-testid` values are stable by convention, not contract; the
  live-probe gate before enablement is what makes them shippable.
- X actively throttles and flags automation; probing and testing must be
  paced like a human, minimal page loads, no rapid retries.
- The banner and avatar inputs are structurally similar; the label-based
  pairing rule is the safety line.
- Layout A/B variants may rename labels; a variant path is a new probe,
  not an assumption.

## Open items for the next live probe

1. Trigger-to-input pairing mechanics: what clicking "Add avatar photo"
   does to the DOM (does it focus/own the file input, open a native
   picker, or mount a new input).
2. The preview structure inside the avatar container after a file is
   staged (img vs canvas) and its pixel-read path.
3. Save enablement semantics: when `aria-disabled` flips after a staged
   file, and whether an unsaved-change confirmation appears on close.
4. Post-save verification signal: avatar `src` change on profile reload,
   and CDN cache delay.
5. Cropping behavior: whether X crops client-side before upload or after,
   which affects the byte-comparison tolerance for verification.

## Verification plan before enablement

- Offline: the synthetic DOM battery gains X fixtures mirroring the
  probed structure, run under both engines, with the same negative cases
  Facebook runs (ambiguous inputs, banner-vs-avatar confusion attempts,
  spoofed previews, missing dialog).
- Live: a dry-run on the maintainer's account stages a real photo into
  the avatar preview and stops before Save, screenshot-verified, exactly
  like the Facebook Prepare verification. Only after that does the adapter
  get enabled in a release, with host permissions broadened deliberately
  and the change called out in the release notes.

# Local profile-photo preparation and export workflow

Date: 2026-10-29. Status: design spec, not implemented.
Supersedes: any plan to enable the LinkedIn DOM automation adapter.

## Why this direction

LinkedIn's user agreement prohibits third-party browser extensions that
automate activity or modify its website, and LinkedIn warns that accounts
may be restricted for using them. The DOM adapter in `src/content.js`
therefore stays behind `enabled: false`, with `uploadAction: null`, for
research and regression testing only. No live probe, staged upload, or
selector verification will run against LinkedIn.

This document specifies the replacement feature: a local photo
preparation and export workflow that gives the user a finished,
privacy-safe image to upload through LinkedIn's own interface, on their
own click.

## Goals

- Import a photo locally (reuse the existing library pipeline).
- Normalize it: square crop, resize, convert to privacy-safe JPEG, strip
  EXIF/GPS metadata. `src/images.mjs` (`normalizePhoto`) already does all
  of this; no new image code is expected.
- Preview the result at platform-specific dimensions before export.
- Export the finished image to disk with one click, clearly named.
- The user uploads it through LinkedIn's own profile-photo flow.

## Non-goals

- No DOM interaction with LinkedIn, ever, in this workflow.
- No scraping, no session use, no navigation to LinkedIn.
- No claims about LinkedIn's upload UI from this extension.

## Proposed UI

A third mode in the existing popup, platform-neutral so X and Instagram
can join later without new UI:

- A "Prepare for export" section listing export targets. LinkedIn is the
  first entry. Each entry names the output spec it prepares for.
- Pick a library photo, press Export, and the browser downloads a single
  JPEG: square, sized to the target's recommended minimum (LinkedIn
  commonly recommends 400x400 px; confirm the current guidance at
  implementation time and record the source).
- The library, rotation, and daily-review features stay Facebook-only
  until another platform has a permitted automation path; export never
  touches rotation state.

## Data flow

1. `listPhotos()` -> user picks a stored photo (or imports a new one).
2. `getPhoto(id)` -> blob.
3. `normalizePhoto(blob)` (existing) -> cropped/resized/metadata-free JPEG.
4. Anchor download with `download` attribute, filename derived from the
   original name plus the target id, sanitized via `safePhotoName`.
5. Nothing is stored, sent, or remembered for the export itself.

## Security and privacy notes

- The exported JPEG carries no camera metadata because `normalizePhoto`
  strips it; add a regression that parses the exported bytes and asserts
  no EXIF segments survive.
- Export runs entirely offline after the photo is read from IndexedDB.
- The download attribute approach needs no new permissions.

## Official integration options (research item)

No LinkedIn API that permits changing a personal profile photo on a
user's behalf is known as of 2026-10-29; the Marketing API does not cover
it. Re-evaluate only against published LinkedIn developer documentation,
and only through a permitted integration path. Until one exists, export
plus manual upload is the whole feature.

## Test plan sketch

- Unit: export filename sanitization; square crop at the target size;
  EXIF-stripped output bytes.
- Battery: export produces a blob of the expected dimensions and type
  using the existing fixture images.
- Manual: import a photo, export for LinkedIn, confirm the downloaded
  file opens and contains no metadata, and upload it to LinkedIn by hand.

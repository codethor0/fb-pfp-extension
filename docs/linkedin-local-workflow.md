# Local profile-photo preparation and export workflow

Date: 2026-10-29. Status: implemented (feature/linkedin-export), pending release.
Supersedes: any plan to enable the LinkedIn DOM automation adapter.
Target size grounded in LinkedIn Help (checked 2026-10-29): profile photo
minimum 400 x 400 px, maximum file size 8 MB.

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
- Transform it for the target platform: center square crop, resize to the
  target's recommended dimensions, convert to privacy-safe JPEG, strip
  EXIF/GPS metadata.
- Preview the result at platform-specific dimensions before export.
- Export the finished image to disk with one click, clearly named.
- The user uploads it through LinkedIn's own profile-photo flow.

## The transform is new code, not normalizePhoto

`normalizePhoto` (src/images.mjs) scales an image down to fit within
`MAX_DIMENSION` and preserves the aspect ratio; it never crops. Verified
against the source on 2026-10-29. The export path therefore needs a
separate transform, proposed as `cropSquareForExport(blob, size)`:

1. Decode with `createImageBitmap` and validate with the same
   `dimensionsSupported` guard `normalizePhoto` uses.
2. Center-crop the shortest side: crop side `s = min(width, height)`,
   source rectangle centered on the image.
3. Draw the crop into a `size x size` canvas with a white background (same
   convention as `normalizePhoto`), export JPEG at 0.88 quality, and cap
   the output with the existing size guard.
4. Pure function over the stored blob: it must not mutate the stored
   photo, touch the library, or share state with the Facebook pipeline.
   Callers pass a copy; the rotation state and IndexedDB records stay
   exactly as they were.

Implementation requirements:

- Live in `src/images.mjs` next to `normalizePhoto`, sharing its guards
  and error style, with unit tests covering: landscape source, portrait
  source, already-square source, odd dimensions (rounding), and a
  regression that parses the exported bytes and asserts no EXIF segments
  survive.
- The Facebook normalization path is not modified by this work.

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
3. `cropSquareForExport(blob, targetSize)` (new, see above) -> square,
   metadata-free JPEG at the target size.
4. Anchor download with `download` attribute, filename derived from the
   original name plus the target id, sanitized via `safePhotoName`.
5. Nothing is stored, sent, or remembered for the export itself.

## Security and privacy notes

- The exported JPEG carries no camera metadata because the canvas
  re-encode drops EXIF; the regression test parses the exported bytes and
  asserts no EXIF segments survive.
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

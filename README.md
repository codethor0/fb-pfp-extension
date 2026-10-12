# fb-pfp: Browser Profile Picture Rotator

A free, open-source Chrome and Brave extension that uses photos you choose to prepare or change your own Facebook profile picture. No developer account, remote service, or Python installation is required. Built for accounts you own, with a local image library and explicit publishing controls.

**Version:** 0.2.1 experimental source candidate. Live Facebook and macOS Brave/Chrome acceptance testing is pending. No browser-store listing or bug-free guarantee is claimed.

## Features

- **Prepare for review** opens your Facebook profile-picture dialog and loads a selected photo without clicking Save.
- **Change profile picture now** requires an explicit checkbox and button click. It attempts to click Save inside the profile-picture dialog, then waits for the dialog to close. Verify the result on Facebook.
- **Rotation** selects randomly or avoids repeating photos after acknowledged Save actions until all have been selected.
- **Daily review** can prepare a photo at a chosen local time when your browser is running. A scheduled run never clicks Save.
- **Private photo library** holds up to 20 locally imported JPEG, PNG or WebP pictures. Each original image must be 8 MB or smaller.
- **On-device processing** converts images to JPEG at up to 1600 pixels, stripping embedded EXIF/GPS metadata. Transparent areas become white.
- **No cloud backend** and no data sent to the developer. Only Chrome/Brave and the Facebook site handle your pictures.

## Install for free (Chrome or Brave)

1. Extract the install ZIP into a permanent folder, such as `~/Projects/fb-pfp-extension`.
2. Open `brave://extensions` in Brave or `chrome://extensions` in Chrome.
3. Enable **Developer mode** in the extensions page.
4. Select **Load unpacked**, then choose the extracted folder containing `manifest.json`.
5. Pin **fb-pfp** in the browser toolbar. Sign in to Facebook normally in the same browser, using the English-language interface.
6. Open the extension, select **Add local pictures**, and import your test photos.
7. Press **Prepare for review** first. Check that the photo reaches the actual profile-picture dialog, not a post composer.
8. Only after verifying the review flow, check the acknowledgment box and press **Change profile picture now** if you want to publish immediately.

Chrome and Brave require the Load unpacked interaction. A command-line script or a separate agent cannot reliably and silently install an unpacked extension into a normal existing browser profile. Your local operator may complete the browser UI steps with your approval.

If an earlier unpacked fb-pfp extension is installed, disable the old copy before loading this build. Data stored under a different extension ID will not migrate automatically. Re-import photos as needed.

## Rotation and scheduling

Select **No repeats after successful Save** or **Random**, then click **Save preferences**. Preparing for review does not advance the rotation. Change now advances it only after the automation receives the Save dialog's closure acknowledgement. This acknowledgement is not independent proof that Facebook published the intended pixels, so confirm the result in your profile.

For optional scheduled preparation, enable **Prepare the picture dialog daily**, choose the local time, and save preferences. The browser must be running. Sleeping or closed browsers cannot guarantee exact execution. Scheduled preparation never publishes automatically.

## Security and privacy

- Permissions: `storage`, `alarms`, and restricted access to `https://www.facebook.com/*`.
- No browser debugging port, password, token or cookie collection.
- Files are stored locally in the browser's extension IndexedDB. Rotation settings are in extension-only Chrome storage.
- Each staged image is handed to a Facebook file input scoped to the profile-picture dialog. Facebook may receive the image **before** Save is clicked.
- Only the user-triggered Change now action may click Save, and only inside the matching dialog.
- The extension never intentionally uploads a file through the newsfeed composer.
- No analytics, third-party JavaScript, advertisements, external telemetry or paid APIs.

See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md).

## Limitations

Facebook changes its interface regularly, so selectors may need maintenance. The current flow uses English UI labels, the `www.facebook.com` origin and the profile-picture dialog. A missing or ambiguous target stops the run. Before reporting Ready for review or attempting Save, it checks that a loaded preview matches samples from the selected image. Unknown, unreadable or unsupported previews stop with manual review guidance. Automated Chrome and Brave lifecycle tests use synthetic pages; live Facebook and the final public avatar still require owner verification.

This extension is not affiliated with, endorsed by, or sponsored by Meta Platforms, Inc. Automating Facebook may conflict with its service terms; use it on your own account at your own risk.

## Development and verification

With Node.js 20+ and Python 3 installed, run **one command**:

```bash
bash verify.sh --full
```

It runs static security checks, 26 dependency-free unit tests, 50 content-flow regressions, popup tests, and a real Manifest V3 lifecycle test in a temporary browser profile. The lifecycle test checks all three image formats, metadata removal, exact photo persistence after browser restart, rotation and scheduled review. Synthetic Save controls are exercised; no real Facebook account or public picture is changed. It installs test-only Python packages and Playwright Chromium locally when needed.

```bash
bash verify.sh --offline    # Run mock-page tests without extension-worker lifecycle
bash verify.sh --quick      # Node static checks and unit tests only
python3 tools/build_release.py --out dist
```

Makefile shortcuts are `make quick`, `make test`, `make verify` and `make package`. They never act on real Facebook, call the separate CLI, commit code or publish a release.

A **full test must report PASS**, not SKIP, before claiming extension lifecycle verification. Leave `CHROMIUM_PATH` unset for bundled Playwright Chromium, or set it to your installed Chrome or Brave executable. Branded Chrome uses pipe-only extension loading in the disposable profile. `VERIFY_PYTHON` may select an existing Python with Playwright and Pillow. These tests do not replace a test against your own Facebook account. See [VERIFICATION.md](VERIFICATION.md).

## Releasing

Keep the existing Python CLI repository separate. Publish extensions from the maintainer's authenticated `codethor0` workflow, after passing CI, the privacy scan, and the manual acceptance checklist. Development workspaces, local paths, personal photos, private screenshots and tooling transcripts do not belong in the public repo. Do not rewrite existing release history without a separate documented decision.

The source may be released for free on GitHub. Chrome Web Store registration requires a one-time developer fee (typically USD $5) and acceptance is not guaranteed. A real account acceptance test and a separate review of platform terms must precede public publication. For more information, see [docs/chrome-web-store.md](docs/chrome-web-store.md), [docs/distribution.md](docs/distribution.md), and [docs/release-checklist.md](docs/release-checklist.md).

## License

[MIT](LICENSE). Copyright 2026 codethor0.

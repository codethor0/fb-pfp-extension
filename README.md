# fb-pfp: Profile Picture Cycler (browser extension)

A small, open-source browser extension that changes your Facebook profile picture from a set of images you pick. Local only: no accounts, no servers, no analytics, no tracking. Everything happens in your own browser, and the only network destination is facebook.com itself.

MIT licensed, free forever. Not published to browser stores: install it yourself in under two minutes (below).

## How it works

1. Click the extension icon and pick two or more images. They are stored inside your browser's local storage.
2. Click "Dry run" to upload the chosen image into Facebook's profile-picture dialog and stop before Save. Nothing is published.
3. Click "Change profile picture now" to do it for real. One image is chosen at random, with no repeats until every image has been used.
4. The extension drives the "Choose profile picture" dialog in a normal tab, clicks Save, and reports success only after the dialog closes.

## Install (Brave or Chrome, sideload)

1. Download or clone this repository.
2. Open `brave://extensions` (or `chrome://extensions`).
3. Turn on **Developer mode** (top right).
4. Click **Load unpacked** and select this folder.
5. Pin the extension, pick images, and run a dry run first.

## Safety design

- The file input is only ever touched inside the profile-picture dialog, never page-wide, so an upload cannot land in a post draft.
- Elements are found by their visible text, not generated class names.
- An image counts as used only after the change succeeds; a failed run does not consume it.
- No credentials are read, stored or sent. The extension never talks to anything except the facebook.com tab it drives.

## Limitations

- Facebook changes its pages without notice; if the dialog labels change, a run can fail with "did not appear". Open an issue with what you saw.
- Images live in browser storage. Very large sets may hit browser storage limits; a handful of photos is the intended use.
- Automating Facebook may conflict with Meta's terms of service. Use it on an account you own, at your own risk. This is why the extension is sideloaded rather than store-distributed.

## Disclaimer

Not affiliated with, endorsed by, or sponsored by Meta Platforms, Inc. Facebook is a trademark of Meta Platforms, Inc.

## Development

The content script is covered by an end-to-end test that runs it against a mock of the Facebook dialog (no real Facebook, no account needed):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tests/test_content.py
```

Bug reports and pull requests are welcome.

## License

[MIT](LICENSE)

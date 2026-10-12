# Chrome Web Store submission: steps, costs, and honest expectations

## Costs (as of October 2026)

- Google Chrome Web Store developer registration: **$5 one-time**. No subscription, no per-update fee, no percentage of anything. This is the "small fee" you heard about. Payment is via your Google account (card/Google Pay) at registration.
- Brave: no fee. Brave pulls from the Chrome Web Store and also runs its own add-ons page, which accepts direct submissions free.

Everything else is free: the extension is MIT, GitHub hosting is free, and updates to an already-published item are free.

## Steps

1. Register at the [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole/) with your Google account. Pay the $5 one-time fee.
2. Create a ZIP of the extension folder: `manifest.json`, `popup.html`, `popup.js`, `content.js`, `icons/`. Nothing else.
3. "New item" in the dashboard, upload the ZIP.
4. Fill in the listing: description, 1280x800 screenshot (you can capture the popup), category (Social Networking or Productivity), language.
5. Declare permissions justification: the reviewer will ask why `storage`, `unlimitedStorage`, `scripting`, `activeTab`, and the facebook.com host permission are needed. Answer plainly: images are stored locally; the content script drives the profile-picture dialog on the user's own account after an explicit click; nothing is transmitted anywhere.
6. Submit for review. Typical review: a few days to two weeks.
7. For Brave: after the CWS item is live it is installable in Brave. Optionally also submit to the Brave add-ons page (free).

## Automated releases from the command line

After the item exists in the dashboard, every future update is one command:

```bash
make release
```

This builds the store zip, uploads it, and submits it for review. It requires
a one-time credential setup (about 15 minutes, done once):

1. In the [Google Cloud Console](https://console.cloud.google.com/) (with the
   same Google account as the publisher), create a project and enable the
   **Chrome Web Store API**.
2. Configure the OAuth consent screen: type External, app name anything, your
   email as support and developer contact, add the scope
   `https://www.googleapis.com/auth/chromewebstore`, add yourself as a test
   user. Leave the app in Testing mode for personal use.
3. Create an OAuth client ID of type **Web application** and add this
   authorized redirect URI:
   `https://developers.google.com/oauthplayground/oauth2callback`
4. Open the [OAuth Playground](https://developers.google.com/oauthplayground/),
   click the gear icon, check "Use your own OAuth credentials", and paste the
   client ID and secret. In the left panel select scope
   `https://www.googleapis.com/auth/chromewebstore`, click "Authorize APIs"
   (sign in with the publisher Google account), then "Exchange authorization
   code for tokens". Copy the refresh token.
5. Write the credentials to `~/.config/fb-pfp/cws.env` (chmod 600):

   ```
   CWS_CLIENT_ID=...
   CWS_CLIENT_SECRET=...
   CWS_REFRESH_TOKEN=...
   CWS_PUBLISHER_ID=...   # from the dashboard Settings page
   CWS_EXTENSION_ID=...   # the item ID, visible in the dashboard item URL
   ```

Notes and limits, stated plainly:

- The API cannot create items, only update and publish existing ones. That is
  why the first upload is manual (the steps above).
- The old v1 API is shut down on October 15, 2026; the script uses the v2
  endpoints.
- Every upload must bump `version` in manifest.json. `make release` refuses
  to republish the same version unless you pass `--force` through
  `python3 tools/cws_release.py release --zip <zip> --force`.
- The script prints secrets never. Keep `cws.env` out of any repository.
- `python3 tools/cws_release.py status` shows the current store state without
  changing anything.

## Honest expectations (read before submitting)

- The extension's purpose is automating a Facebook action. Meta's terms prohibit that kind of automation, and store reviewers can reject or later remove items whose function violates a third-party site's terms, especially after reports. This is a policy risk, not a malware finding.
- Mitigations that genuinely help: the extension acts only on an explicit click, only on the site named in host permissions, stores nothing remotely, and carries a clear disclaimer in the listing. Do not obscure what the extension does; disguised-functionality rejections are permanent strikes against the developer account.
- The blast radius of a rejection is limited to this $5 account, which is why the listing should live under a dedicated Google account rather than your personal one.
- Fallback distribution either way: the sideload install in the README. It works today, costs nothing, and cannot be delisted. Treat the store listing as convenience, not survival.

## Pre-submission checklist (all must be green)

- `make test` passes (syntax, manifest, end-to-end mock).
- No absolute paths, no tool names, no personal identifiers in any file (a recursive grep for a home-directory prefix such as `"/Users"` returns nothing).
- Icons present in all three sizes; manifest version bumped.
- One live dry-run against your real Facebook passed.
- Meta non-affiliation disclaimer visible in the store description.
- Privacy policy published (PRIVACY.md in this repository); the Privacy tab
  points to `https://github.com/codethor0/fb-pfp-extension/blob/main/PRIVACY.md`.

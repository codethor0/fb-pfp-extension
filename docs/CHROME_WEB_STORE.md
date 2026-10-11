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

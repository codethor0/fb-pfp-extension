# Chrome Web Store submission (maintainer checklist)

Last reviewed: 2026-10-11. The extension is a source candidate, not an approved store item.

## Developer registration and costs

- Developer dashboard: https://chrome.google.com/webstore/devconsole
- Google requires a one-time developer registration fee, commonly USD $5. The dashboard checkout is authoritative for your account and region. No monthly hosting or paid API is needed for this extension.
- Create or sign in to a Google account that you control, enable two-step verification, accept the developer agreement, and pay the one-time registration fee yourself. Register under your preferred public developer identity; a GitHub username does not automatically become a verified Google developer identity.
- Google may require further identity verification. Registration, payment and developer verification are not tasks to bypass or silently automate.

## Pre-submission policy gates

- Verify that the extension's actual behavior is permitted by both the current Meta terms and Chrome Web Store policy. User consent alone does not establish Meta authorization. If prohibited or unclear, defer the listing or change the functionality before submission.
- Run `bash verify.sh --full` and require every gate to PASS. Then complete separately approved, live tests in actual Brave and Chrome. These are not covered by the offline mock tests.
- Confirm minimum permissions (`storage`, `alarms`, `https://www.facebook.com/*`), no remote code, no tracking, and a truthful privacy policy.
- Confirm all images, logs, personal paths, agent workspace references and credentials are absent from the source and Git history, including old commits and public PR diffs.
- Integrate via a reviewed `codethor0` PR after passing CI. Only the authenticated maintainer can commit, push, tag and publish.

## Build and upload

1. Generate reproducible archives: `python3 tools/build_release.py --out dist`.
2. Upload `dist/fb-pfp-extension-v0.2.2-store.zip`. Its manifest is at the ZIP root. **Do not** upload the install ZIP, which has an enclosing folder, or the source ZIP, which includes developer tests.
3. In the Chrome Web Store developer dashboard, create a new item and upload the store ZIP.
4. Complete Store listing: product name, short and detailed description, English language, category, 128 x 128 icon, and accurate screenshots of the extension working. Google may require additional assets. Do not supply images containing someone's private Facebook profile or credentials.
5. Complete Privacy practices: document access to Facebook profile-page UI, storage of imported images and preferences on the user's device, image handoff to Facebook, absence of publisher telemetry, and why the requested host access is required. Publish the public privacy policy at a stable URL, for example `https://github.com/codethor0/fb-pfp-extension/blob/main/PRIVACY.md` only after it matches the shipped source.
6. Set homepage and support link to the project's public GitHub repository and Issues page if you offer public support.
7. Set Distribution visibility, locations and pricing (Free), review all disclosures, then **Submit for Review**. You can choose deferred publication after approval.
8. Await Google's review outcome. Approval time and outcome cannot be guaranteed. Do not claim an official listing until the Chrome Web Store provides its public listing URL.

## Sources

- Registration: https://developer.chrome.com/docs/webstore/register/
- Package preparation: https://developer.chrome.com/docs/webstore/prepare
- Privacy: https://developer.chrome.com/docs/webstore/user_data
- Store rules: https://developer.chrome.com/docs/webstore/program-policies
- Listing: https://developer.chrome.com/docs/webstore/cws-dashboard-listing
- Distribution: https://developer.chrome.com/docs/webstore/cws-dashboard-distribution
- Terms review: https://www.facebook.com/legal/terms

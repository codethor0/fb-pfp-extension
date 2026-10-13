# Security policy

## Supported release

Version 0.2.2 completed the automated battery (60 checks from a clean clone) and the live review-flow acceptance test on the owner account on 2026-10-12. A public Save test remains an explicit owner decision. Only the latest source release receives planned fixes.

## Security boundaries

The extension uses a strict Facebook HTTPS host permission, browser storage, and a local alarm. No remote executable code, native messaging, browser debugging ports, credentials, cookies, password collection or analytics are used. Imported images are re-encoded as JPEG to strip metadata before storing them.

Every upload input is looked up inside a uniquely matched profile-picture dialog. The content script does not interact with unrelated page-wide file inputs, rejects messages not sent by this extension, and only uses file inputs that declare image types. It fails closed on ambiguous avatar matches. **Prepare for review** and the optional alarm never click Save. **Change now** requires direct user confirmation in the popup and may click Save inside the profile-picture dialog. A Save click that Facebook never confirms counts the photo as used without claiming confirmation. Successful dialog closure is an acknowledgement, not cryptographic or server-side proof of publication.

## Risk model

Main risks include a maliciously modified extension, compromised browser profile, unexpected Facebook UI variants, choosing an unintended photo, and Facebook receiving a staged image before the Save click. Scheduled runs open tabs and may be delayed if the computer sleeps. Use only trusted release files, test with a harmless photo, and check the final profile before relying on automated updates.

## Responsible disclosure

Use the repository's private GitHub security advisory mechanism for sensitive bug reports. Do not post tokens, personal photographs, account screenshots, browser profiles, or private URLs in public issues. Avoid sharing exact paths to private workspaces.

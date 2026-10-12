# Security policy

## Supported release

Version 0.2.1 is a local-testing source candidate. It has not completed the live Facebook and macOS browser acceptance gates. Only the latest source release receives planned fixes.

## Security boundaries

The extension uses a strict Facebook HTTPS host permission, browser storage, and a local alarm. No remote executable code, native messaging, browser debugging ports, credentials, cookies, password collection or analytics are used. Imported images are re-encoded as JPEG to strip metadata before storing them.

Every upload input is looked up inside a uniquely matched profile-picture dialog. The content script does not interact with unrelated page-wide file inputs and fails closed on ambiguous avatar matches. **Prepare for review** and the optional alarm never click Save. **Change now** requires direct user confirmation in the popup and may click Save inside the profile-picture dialog. Successful dialog closure is an acknowledgement, not cryptographic or server-side proof of publication.

## Risk model

Main risks include a maliciously modified extension, compromised browser profile, unexpected Facebook UI variants, choosing an unintended photo, and Facebook receiving a staged image before the Save click. Scheduled runs open tabs and may be delayed if the computer sleeps. Use only trusted release files, test with a harmless photo, and check the final profile before relying on automated updates.

## Responsible disclosure

Use the repository's private GitHub security advisory mechanism for sensitive bug reports. Do not post tokens, personal photographs, account screenshots, browser profiles, or private URLs in public issues. Avoid sharing exact paths to private workspaces.

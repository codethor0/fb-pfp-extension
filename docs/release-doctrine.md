# Release doctrine

Rules and release gates for the fb-pfp project. Everything here applies to
the extension repository and the companion CLI repository. The goal is a
secure, honest, boring codebase that survives store review and public
scrutiny.

## 1. Secure coding

1. Fail closed. An ambiguous target, an unreadable preview, a replaced
   dialog or an unexpected page state stops the run with a plain error. Never
   guess and never click Save on a guess.
2. No remote code. All JavaScript ships inside the package. No external
   script tags, no dynamic imports of remote URLs, no eval, no new Function.
3. No secrets in the repository. No API keys, tokens, passwords, private
   keys, session files or personal photos. The release tooling scans for
   these markers on every build.
4. Least privilege. Request the minimum permissions and host access the
   feature needs. Every permission carries a written justification that
   matches what the code actually does.
5. Validate every input. Filenames are sanitized, image bytes are parsed
   before use, dimensions and sizes are bounded, and stored records carry
   only display metadata.
6. Subprocess discipline (CLI). Fixed argument lists only, never a shell,
   never string concatenation with variable input.
7. Attribution discipline. An upload input is used only when the
   profile-picture dialog or its own upload button caused it, only when it
   accepts images alone, and the capture listener is released afterwards.

## 2. Privacy

1. Local first. Photos and state stay in the browser or on the machine.
   Nothing is sent to the developer; there is no server and no analytics.
2. The privacy policy states exactly what the current version does, no more
   and no less. Any behavior change updates the policy before release.
3. Declarations in the store dashboard must match the policy and the code.
   If the code does not collect a data category, the box stays unchecked.

## 3. Store compliance

1. Single purpose. The extension does one thing and the listing says so.
2. Honest listing. No promised features that the build does not have, no
   inflated claims, no fake reviews, no growth hacks.
3. Respect third-party terms. The listing states that the project is not
   affiliated with or endorsed by Meta Platforms, Inc., and that automation
   may conflict with Facebook terms.
4. Permission justifications are concrete and truthful.
5. The store package, the public repository, the listing text, the
   screenshots and the privacy policy all describe the same build. Reconcile
   them before every submission.

## 4. Documentation standards

1. Plain ASCII prose. No em dashes, no en dashes, no smart quotes.
2. No filler and no hype. State what the software does, what it does not
   do, and what the user must verify.
3. Never claim zero bugs. Report what was tested, on what date, and what
   remains unverified.
4. Every version bump updates the changelog and the verification record.
5. README, security policy, contributing guide and support links stay
   current and reachable.

## 5. Repository hygiene

1. No machine-specific absolute paths, no transcripts, no screenshots of
   private accounts, no third-party working files.
2. Commits carry a clean maintainer identity. History is never rewritten
   after publication.
3. CI must be green on the default branch. A full verification run from a
   clean clone must pass before any release or store submission.

## 6. Release gates

A release or store submission requires all of the following:

- [ ] `bash verify.sh --full` reports PASS from a clean clone
- [ ] Fresh-clone proof captured on the release day
- [ ] Privacy policy, listing and declarations reconciled with the build
- [ ] Live review-flow acceptance on the owner account for the exact build
- [ ] Public Save changes require an explicit owner decision
- [ ] Changelog and verification record updated

When in doubt, do not ship.

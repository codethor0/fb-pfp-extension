# Verification record

Date: 2026-10-12
Version: 0.2.1
Status: STORE REVIEW PENDING; LIVE REVIEW FLOW VERIFIED ON OWNER ACCOUNT

## Completed automated checks

- Static manifest, minimum permissions and repository hygiene audit passed.
- All 26 dependency-free Node tests passed.
- All 50 synthetic content regressions passed in installed Chrome and Brave on macOS.
- Popup import/removal, confirmation, review and schedule controls passed in both browsers.
- Full Manifest V3 lifecycle passed in Chrome 155.0.8059.40 and Brave 155.1.97.56 using disposable profiles.
- JPEG, PNG and WebP imported as normalized JPEGs without the synthetic camera metadata.
- Exact stored photo bytes and rotation history survived popup and browser/service-worker restart.
- Review left Save and rotation history untouched. Two successful synthetic Saves advanced no-repeat rotation without repeating.
- An actual alarm prepared the synthetic picture without Save or rotation advancement; disabling the schedule removed the alarm.
- Delayed/replaced dialogs, ignored/rejected uploads, unrelated gallery images, ambiguous inputs, untrusted input requests, cancellation and incomplete Save closure have regressions.
- Selected-image sampling supports the tested full previews, resized images, centered square crops and reused canvas forms. Unreadable or unsupported previews stop for manual review.
- Test browsers map www.facebook.com to local HTTPS fixtures and make other hosts unresolvable. No real account or public avatar was changed.
- Release packaging checks manifest-at-root, allowlisted runtime files and exclusion of private media, credentials and machine-specific paths.

## Completed live acceptance

- On 2026-10-12 the packaged build was loaded into the owner's Brave session and run against the owner's real Facebook account with the English interface.
- Prepare for review opened the real profile-picture dialog with the selected library photo loaded in the cropper. The post composer was untouched and Save was never clicked.
- The dialog was dismissed without changes; the public profile picture was confirmed unchanged afterwards.

## Remaining acceptance gates

- A public Save test (Change profile picture now) still requires an owner decision and inspection of the resulting profile picture. No live Save has been performed or claimed.
- A Save acknowledgement is dialog completion after an explicit click. It does not independently prove Facebook persisted the intended avatar.
- Browser sleep, future interface variants, profile upgrades and unreadable cropper forms remain outside the verified synthetic cases.
- The store item was submitted for review on 2026-10-12 with automatic publication after approval. Store acceptance is up to Google and has not occurred as part of this verification.

## Release rule

Keep publication under the authenticated publisher workflow. Do not claim zero bugs or automatic verification of the final public avatar.

# Privacy Policy for fb-pfp

Effective date: October 11, 2026

fb-pfp ("the extension") is an open-source browser extension that helps you
change the profile picture on your own Facebook account. This policy describes
what data the extension touches, where it lives, and where it goes. The short
version: everything happens on your device, and the developer never sees any
of it.

## Data the extension stores (on your device only)

- Photos you import are stored locally in your browser's extension storage
  (IndexedDB). They never leave your device except as described below.
- Preferences and state: your rotation mode, the optional daily schedule if
  you turn it on, which pictures have already been used, and the status of
  the last operation. This is kept in local extension storage.

## What the extension sends, and where

- The extension has no servers. It does not send your photos, preferences, or
  any other data to the developer or to any third party.
- When you run the extension on Facebook, the selected photo is placed into
  Facebook's own profile picture upload control. From that moment, the photo
  may be transmitted to Facebook (Meta Platforms, Inc.) under Facebook's own
  terms and privacy policy, even if you do not click Save. That transfer is
  between you and Facebook; the developer cannot see it, control it, or opt
  you out of it.
- The optional daily schedule only prepares a picture for your review. It
  never clicks Save and never changes your profile picture without you.

## What the developer collects

Nothing. No analytics, no crash reporting, no tracking, no ads, no account
system. There is nothing for the developer to receive and no account to
associate it with.

## Permissions and why they exist

- storage and unlimitedStorage: keep your imported photos and local state in
  the browser.
- alarms: run the optional daily schedule you enable.
- scripting and activeTab: operate the profile picture dialog on
  www.facebook.com only after you click the extension.
- Host permission for www.facebook.com: the only site the extension can
  touch.

## Data retention and deletion

Everything the extension stores lives on your device. Uninstalling the
extension deletes its storage, including all imported photos. You can also
clear photos inside the extension at any time.

## Security

The extension is local-only, which removes most attack surface: there is no
server, no database of users, and no credential handling. The source code is
public at https://github.com/codethor0/fb-pfp-extension and can be audited by
anyone.

## Children

The extension is not directed at children and does not knowingly handle data
from children.

## Changes to this policy

If the extension's data handling ever changes, this file is updated before
the corresponding release is published. Version control keeps every revision
visible.

## Contact

Open an issue at https://github.com/codethor0/fb-pfp-extension/issues. That
is the fastest way to reach the maintainer.

## Disclaimer

This is an independent open-source project. It is not affiliated with,
endorsed by, or sponsored by Meta Platforms, Inc. or Google.

# Automated verification

## One command

From the source project directory, run `make verify` or:

```bash
bash verify.sh --full
```

The command requires Node.js 20+ and Python 3. It sets up free test-only Python packages, installs Playwright Chromium when needed, and then runs static checks, Node tests, offline page tests and a full-extension lifecycle test against an offline fixture. It does not connect to Facebook, install into your existing Chrome/Brave profile, click a real Save, or push to GitHub.

A full run must exit code 0 and print the final PASS line. Any error or missing browser is a failed or unverified gate, never an implicit PASS.

For an environment with an existing system Chromium binary, run:

```bash
CHROMIUM_PATH=/path/to/chromium bash verify.sh --offline
```

`--offline` runs all previously verified mock tests, but **does not** prove that the MV3 service worker loads. For syntax and Node unit checks only, run `bash verify.sh --quick`.

## Mac acceptance testing

A fully unattended test against an already authenticated Brave profile is not equivalent to the isolated offline tests. It would require privileged browser integration, could act on a public profile and may violate platform policies. Browser vendors deliberately require user consent to install an unpacked extension. A local operator may automate ordinary GUI navigation with the owner's approval, but must not bypass approval, take a screenshot of private profile data for a public repository, or click Save without explicit permission.

Before a production announcement, test both browsers using a harmless photo, verify the correct profile, ensure the newsfeed composer remains untouched, check that a preview stops before Save, and explicitly verify a real authorized Save in the intended account. Record the outcome privately.

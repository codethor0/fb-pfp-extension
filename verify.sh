#!/usr/bin/env bash
# One command for local, non-publishing extension verification.
set -Eeuo pipefail
cd "$(dirname "$0")"
mode="${1:---full}"
case "$mode" in --quick|--offline|--full) ;; *) echo "Usage: bash verify.sh [--quick|--offline|--full]" >&2; exit 2 ;; esac
if ! command -v node >/dev/null 2>&1; then
  echo 'BLOCKED: Node.js 20+ is required. Install Node.js and retry.' >&2
  exit 2
fi
printf '\n[1/4] Static security, package and Node unit tests\n'
node tools/audit.mjs
node --test tests/*.test.mjs
if [ "$mode" = --quick ]; then
  echo 'PASS: quick tests. Browser interaction not verified (--offline or --full required).'
  exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo 'BLOCKED: Python 3 is required for browser tests.' >&2
  exit 2
fi
# Install free test-only packages into a project-local, gitignored environment.
venv='.verify-venv'
if [ -n "${VERIFY_PYTHON:-}" ]; then
  python="$VERIFY_PYTHON"
  "$python" -c 'import playwright, PIL' || { echo 'VERIFY_PYTHON must provide Playwright and Pillow' >&2; exit 2; }
elif python3 -c 'import playwright, PIL' >/dev/null 2>&1; then
  python='python3'
else
  if [ ! -x "$venv/bin/python" ]; then python3 -m venv "$venv"; fi
  python="$venv/bin/python"
  if ! "$python" -c 'import playwright, PIL' >/dev/null 2>&1; then
    printf '\n[2/4] Installing isolated, free browser-test dependencies\n'
    "$python" -m pip install -q 'playwright==1.57.0' 'Pillow>=11,<13'
  fi
fi
if [ -z "${CHROMIUM_PATH:-}" ]; then
  printf '\n[2/4] Checking bundled Playwright Chromium\n'
  # Browser installation is idempotent and stays in Playwright's user cache.
  "$python" -m playwright install chromium
fi
printf '\n[3/4] Offline Facebook DOM + popup mock tests\n'
"$python" tools/browser_smoke.py
"$python" tools/popup_smoke.py
if [ "$mode" = --offline ]; then
  echo 'PASS: offline script tests. Full extension-worker test not run (--full required).'
  exit 0
fi
printf '\n[4/4] Actual MV3 service worker, popup, storage and tab test (offline fixture)\n'
"$python" tools/extension_smoke.py
printf '\nPASS: all available automated checks. This does not test live Facebook or Web Store approval.\n'

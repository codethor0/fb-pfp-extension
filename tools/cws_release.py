#!/usr/bin/env python3
"""Command-line releases to the Chrome Web Store (API v2).

Subcommands:
  status            Show the item's upload/publish state.
  upload --zip Z    Upload a new package (must bump manifest version).
  publish           Submit the staged package for review/publication.
  release --zip Z   upload + publish, with a version guard.

Credentials are read from environment variables or, if present, from an
env file (default ~/.config/fb-pfp/cws.env, override with CWS_ENV).
Real environment variables always win over the file.

Required values:
  CWS_CLIENT_ID       OAuth client ID
  CWS_CLIENT_SECRET   OAuth client secret
  CWS_REFRESH_TOKEN   OAuth refresh token (scope: chromewebstore)
  CWS_PUBLISHER_ID    Chrome Web Store publisher ID
  CWS_EXTENSION_ID    Item ID of the existing store item

Secrets are never printed. Only stdlib is used.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_ROOT = "https://chromewebstore.googleapis.com"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/chromewebstore"

DEFAULT_ENV_FILE = Path.home() / ".config" / "fb-pfp" / "cws.env"

REQUIRED_VARS = (
    "CWS_CLIENT_ID",
    "CWS_CLIENT_SECRET",
    "CWS_REFRESH_TOKEN",
    "CWS_PUBLISHER_ID",
    "CWS_EXTENSION_ID",
)

EXIT_CONFIG = 2


def load_env_file(path):
    """Populate os.environ from KEY=VALUE lines; real env vars win."""
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"cannot read env file {path}: {exc}")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def fail(message, code=1):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def require_config():
    missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
    if missing:
        hint = (
            "set the variables in your environment or in "
            f"{DEFAULT_ENV_FILE} (see docs/CHROME_WEB_STORE.md)"
        )
        fail(f"missing configuration: {', '.join(missing)}\n{hint}", EXIT_CONFIG)


def get_access_token():
    body = urllib.parse.urlencode(
        {
            "client_id": os.environ["CWS_CLIENT_ID"],
            "client_secret": os.environ["CWS_CLIENT_SECRET"],
            "refresh_token": os.environ["CWS_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = urllib.request.Request(TOKEN_URL, data=body)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if "invalid_grant" in detail:
            fail(
                "token refresh rejected (invalid_grant): the refresh token "
                "is wrong, expired, or was issued for a different account. "
                "Mint a new one per docs/CHROME_WEB_STORE.md."
            )
        fail(f"token refresh failed with HTTP {exc.code}")
    except urllib.error.URLError as exc:
        fail(f"token refresh failed: {exc.reason}")
    token = payload.get("access_token")
    if not token:
        fail("token response contained no access_token")
    return token


def api_request(method, url, token, data=None, content_type=None):
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"{method} {url} failed with HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        fail(f"{method} {url} failed: {exc.reason}")
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        fail(f"{method} {url} returned non-JSON response")


def item_base():
    pub = os.environ["CWS_PUBLISHER_ID"]
    ext = os.environ["CWS_EXTENSION_ID"]
    return f"{API_ROOT}/v2/publishers/{pub}/items/{ext}"


def manifest_version():
    manifest = Path(__file__).resolve().parent.parent / "manifest.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {manifest}: {exc}")
    version = data.get("version")
    if not version:
        fail(f"manifest.json has no version field")
    return version


def published_version(status):
    try:
        channels = status["publishedItemRevisionStatus"]["distributionChannels"]
        return channels[0].get("crxVersion")
    except (KeyError, IndexError, TypeError):
        return None


def cmd_status(token, _args):
    status = api_request("GET", f"{item_base()}:fetchStatus", token)
    upload_state = status.get("uploadState", "UNKNOWN")
    print(f"upload state:   {upload_state}")
    pub = published_version(status)
    if pub:
        print(f"published version: {pub}")
    local = manifest_version()
    print(f"local version:  {local}")


def cmd_upload(token, args):
    zip_path = Path(args.zip)
    if not zip_path.is_file():
        fail(f"zip not found: {zip_path}")
    pub = os.environ["CWS_PUBLISHER_ID"]
    ext = os.environ["CWS_EXTENSION_ID"]
    url = f"{API_ROOT}/upload/v2/publishers/{pub}/items/{ext}:upload"
    result = api_request(
        "POST",
        url,
        token,
        data=zip_path.read_bytes(),
        content_type="application/zip",
    )
    state = result.get("uploadState", "UNKNOWN")
    print(f"upload state: {state} ({zip_path.name})")
    if state not in ("SUCCESS", "IN_PROGRESS", "UPLOAD_IN_PROGRESS"):
        fail(f"upload did not succeed: {result}")


def cmd_publish(token, _args):
    result = api_request("POST", f"{item_base()}:publish", token)
    print(json.dumps(result, indent=2) if result else "publish submitted")


def cmd_release(token, args):
    if not args.force:
        status = api_request("GET", f"{item_base()}:fetchStatus", token)
        pub = published_version(status)
        local = manifest_version()
        if pub == local:
            fail(
                f"store already has version {local}; bump manifest.json "
                "version or pass --force"
            )
    cmd_upload(token, args)
    cmd_publish(token, args)


def main():
    parser = argparse.ArgumentParser(
        description="Chrome Web Store releases from the command line."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show item state")
    for name in ("upload", "release"):
        p = sub.add_parser(name, help=f"{name} a package")
        p.add_argument("--zip", required=True, help="path to the store zip")
    sub.add_parser("publish", help="submit staged package")
    parser.add_argument(
        "--force",
        action="store_true",
        help="skip the version guard (release only)",
    )
    args = parser.parse_args()

    load_env_file(Path(os.environ.get("CWS_ENV", DEFAULT_ENV_FILE)))
    require_config()
    token = get_access_token()

    handlers = {
        "status": cmd_status,
        "upload": cmd_upload,
        "publish": cmd_publish,
        "release": cmd_release,
    }
    handlers[args.command](token, args)


if __name__ == "__main__":
    main()

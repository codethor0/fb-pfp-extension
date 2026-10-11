.PHONY: test verify dist release

ZIP = fb-pfp-extension-store.zip
ZIP_CONTENTS = manifest.json popup.html popup.js content.js icons

# Automated verification: JS syntax, manifest validity, and the end-to-end
# content-script test against a mock of the Facebook dialog. No real
# Facebook account needed; nothing is published.
test:
	node --check popup.js
	node --check content.js
	python3 -c "import json; json.load(open('manifest.json')); print('manifest OK')"
	python3 tests/test_content.py

# Live check against your real Facebook (manual confirmation by design:
# this drives your real profile). Dry run stops before Save.
# Set NAME to your Facebook display name first.
verify:
	@test -n "$(NAME)" || (echo "usage: make verify NAME=\"Your Facebook Name\"" && exit 2)
	FB_PFP_EXPECTED_NAME="$(NAME)" fb-pfp --dir $(PICS) --dry-run -v
	@echo "If the image reached the dialog, run again without --dry-run to confirm Save."

# Build the store upload zip (exactly the files the store needs, nothing else).
dist:
	rm -f $(ZIP)
	zip -qr $(ZIP) $(ZIP_CONTENTS) -x '.*'
	@unzip -l $(ZIP)

# One-command release: build the zip, upload it, and submit for review.
# Requires one-time setup documented in docs/CHROME_WEB_STORE.md.
# Bump manifest.json version first; the store rejects same-version uploads.
release: dist
	python3 tools/cws_release.py release --zip $(ZIP)

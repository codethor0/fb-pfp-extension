.PHONY: test quick verify package

# No publishing or real Facebook actions. All verification uses synthetic data.
quick:
	bash verify.sh --quick

test:
	bash verify.sh --offline

verify:
	bash verify.sh --full

package:
	python3 tools/build_release.py --out dist

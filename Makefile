.PHONY: help clean tests packages

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  clean     to cleanup build and temporary files"
	@echo "  tests     to run the test suite"
	@echo "  packages  to build python source and egg packages"

clean:
	@rm -rf build dist sahriswiki.egg-info sahriswiki/__version__.py
	@rm -rf .coverage coverage
	@find . -name '*.pyc' -delete
	@find . -name '*.pyo' -delete
	@find . -name '*~' -delete

packages:
	@tools/mkpkgs -p python2.6

tests:
	@py.test -x -r fsxX \
		--ignore=tmp \
		--pastebin=all \
		--cov=sahriswiki \
		--cov-html \
		--cov-html-dir=coverage \
		--cov-no-terminal
		tests/

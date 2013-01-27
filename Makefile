.PHONY: help clean graph packages tests

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  clean     to cleanup build and temporary files"
	@echo "  graph     to generate dependency graph"
	@echo "  packages  to build python source and egg packages"
	@echo "  tests     to run the test suite"

clean:
	@rm -rf build dist sahriswiki.egg-info
	@rm -rf .coverage coverage
	@find . -name '*.pyc' -delete
	@find . -name '*.pyo' -delete
	@find . -name '*~' -delete

graph:
	@sfood sahriswiki -i -I tests -d -u 2> /dev/null | sfood-graph | dot -Tps | ps2pdf - > sahriswiki.pdf

packages:
	@tools/mkpkgs -p python2.6
	@tools/mkpkgs -p python2.7
	@tools/mkpkgs -p python3.1
	@tools/mkpkgs -p python3.2

tests:
	@python -m tests.main

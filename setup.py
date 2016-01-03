#!/usr/bin/env python

from os import path

from setuptools import setup, find_packages

root = path.abspath(path.dirname(__file__))

try:
    README = open(path.join(root, "README.rst")).read()
    RELEASE = open(path.join(root, "RELEASE.rst")).read()
except IOError:
    README = RELEASE = ""


def parse_requirements(filename):
    with open(filename, "r") as f:
        for line in f:
            if line.startswith("git+http"):
                continue
            if line and line[:2] not in ("#", "-e"):
                yield line.strip()


setup(
    name="sahriswiki",
    version="0.9.0",
    description="A Lightweight Wiki Engine using circuits.web",
    long_description="%s\n\n%s" % (README, RELEASE),
    author="James Mills",
    author_email="James Mills, prologic at shortcircuit dot net dot au",
    url="http://sahriswiki.org/",
    download_url="http://github.com/prologic/sahriswiki/downloads/",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Plugins",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.6",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"],
    license="MIT",
    keywords="wiki cms blog engine circuits",
    platforms="POSIX",
    packages=find_packages("."),
    package_data={
        "sahriswiki": [
            "themes/*/templates/*.html",
            "themes/*/htdocs/css/*.css",
            "themes/*/htdocs/img/*.png",
            "themes/*/htdocs/favicon.ico",
            "themes/*/htdocs/img/icons/*.png",
        ]
    },
    include_package_data=True,
    scripts=[
        "scripts/sahriswiki"
    ],
    install_requires=list(parse_requirements("requirements.txt")),
    entry_points={
        "console_script": [
            "sahriswiki = sahriswiki.main:main"
        ]
    },
)

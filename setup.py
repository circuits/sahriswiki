#!/usr/bin/env python

from os import path

from setuptools import setup, find_packages

root = path.abspath(path.dirname(__file__))

try:
    README = open(path.join(root, "README.rst")).read()
    RELEASE = open(path.join(root, "RELEASE.rst")).read()
except IOError:
    README = RELEASE = ""

setup(
    name="sahriswiki",
    version="0.9.0",
    description="A Lightweight Wiki Engine using circuits.web",
    long_description="%s\n\n%s" % (README, RELEASE),
    author="James Mills",
    author_email="James Mills, prologic at shortcircuit dot net dot au",
    url="http://sahriswiki.org/",
    download_url="http://bitbucket.org/prologic/sahriswiki/downloads/",
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
            "templates/*.html",
            "htdocs/css/*.css",
            "htdocs/img/*.png",
            "htdocs/favicon.ico",
            "htdocs/img/icons/*.png",
        ]
    },
    include_package_data=True,
    scripts=[
        "scripts/sahriswiki"
    ],
    entry_points={
        "console_script": [
            "sahriswiki = sahriswiki.main:main"
        ]
    },
    install_requires=[
        "genshi",
        "argparse",
        "circuits",
        "docutils",
        "pygments",
        "mercurial",
        "pyinotify",
        "sqlalchemy",
        "feedformatter",
    ]
)

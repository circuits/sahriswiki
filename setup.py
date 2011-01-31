#!/usr/bin/env python

import os

try:
    from setuptools import setup, find_packages
    HAS_SETUPTOOLS = True
except ImportError:
    from distutils.core import setup
    HAS_SETUPTOOLS = False

if not HAS_SETUPTOOLS:
    import os
    from distutils.util import convert_path

    def find_packages(where=".", exclude=()):
        """Borrowed directly from setuptools"""

        out = []
        stack = [(convert_path(where), "")]
        while stack:
            where, prefix = stack.pop(0)
            for name in os.listdir(where):
                fn = os.path.join(where, name)
                if ("." not in name and os.path.isdir(fn) and 
                        os.path.isfile(os.path.join(fn, "__init__.py"))):
                    out.append(prefix+name)
                    stack.append((fn, prefix + name + "."))

        from fnmatch import fnmatchcase
        for pat in list(exclude) + ["ez_setup"]:
            out = [item for item in out if not fnmatchcase(item, pat)]

        return out

path = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(path, "README.rst")).read()
    HISTORY = open(os.path.join(path, "HISTORY.rst")).read()
except IOError:
    README = HISTORY = ""

setup(
    name="sahriswiki",
    description="A Lightweight Wiki / CMD / Blogging Engine using circuits.web",
    long_description="%s\n\n%s" % (README, HISTORY),
    author="James Mills",
    author_email="James Mills, prologic at shortcircuit dot net dot au",
    url="http://bitbucket.org/prologic/sahriswiki/",
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
            "htdocs/img/icons/*.png",]},
    include_package_data=True,
    scripts=["scripts/sahriswiki"],
    entry_points="""
    [console_scripts]
    sahriswiki = sahriswiki.main:main
    """,
    install_requires = [
        "circuits",
        "docutils",
        "genshi",
        "sqlalchemy",
    ],
    setup_requires=("hgtools",),
    use_hg_version={"increment": "0.01"},
)

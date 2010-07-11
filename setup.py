#!/usr/bin/env python

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

import sahriswiki
from sahriswiki.version import forget_version, get_version, remember_version

forget_version()
remember_version()

setup(
    name="sahriswiki",
    version=get_version(),
    description="A Lightweight Wiki Engine",
    long_description=open("README", "r").read(),
    author=sahriswiki.__author__,
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
    keywords=sahriswiki.__keywords__,
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
    """
)

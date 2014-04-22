# Docker Image for ircnotifier

FROM prologic/crux-python
MAINTAINER James Mills <prologic@shortcircuitnet.au>

# Install Source
RUN pip install https://bitbucket.org/prologic/sahriswiki/get/tip.tar.bz2#egg=sahriswiki

# Expose Service
EXPOSE 8000

# Startup
ENTRYPOINT ["/usr/bin/sahriswiki"]

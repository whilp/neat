"""\
neat is a `WSGI`_ micro framework that encourages API-centric development of web
applications. The framework is especially compatible with `REST`_ services and
APIs, though it can conceivably be used for more or less anything. Applications
implemented with neat are easy to test and produce data that is easy for clients
to consume.

.. _WSGI:   http://wsgi.org/wsgi/
.. _REST:   http://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm
"""

__project__ = "neat"
__version__ = "0.4.1"
__package__ = "neat"
__description__ = "neat WSGI API framework"
__author__ = "Will Maier"
__author_email__ = "willmaier@ml1.net"
__url__ = "http://code.lfod.us/neat"

# See http://pypi.python.org/pypi?%3Aaction=list_classifiers.
__classifiers__ = [
    "Development Status :: 3 - Alpha",
    "Environment :: Web Environment",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 2.6",
    "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
] 
__keywords__ = "neat api rest microframework wsgi"

__requires__ = [
    "WebOb",
]

# The following is modeled after the ISC license.
__copyright__ = """\
Copyright (c) 2010 Will Maier <willmaier@ml1.net>

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

__todo__ = """\
"""

#!/usr/bin/env python3
"""Run the static site locally: python3 server.py [port]."""

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
print(f"Yomu is running at http://localhost:{port}")
ThreadingHTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler).serve_forever()

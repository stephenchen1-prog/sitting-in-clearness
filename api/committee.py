"""Vercel serverless entry point for /api/committee. Reuses the hardened Flask app."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))

from clearness_web import app  # noqa: E402,F401  (Vercel serves the WSGI `app`)

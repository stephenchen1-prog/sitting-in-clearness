"""Vercel entry point: the whole site (page + /api/committee) is the Flask app in server/."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "server"))

from clearness_web import app  # noqa: E402,F401

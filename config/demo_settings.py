"""Opt-in local synthetic demo configuration. Not for deployment or real data."""
import os
from pathlib import Path

os.environ["DJANGO_DEBUG"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).resolve().parent.parent / 'meridian-demo.sqlite3'}"
from .settings import *  # noqa: F403,F401

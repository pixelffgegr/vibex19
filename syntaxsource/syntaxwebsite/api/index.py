"""
Vercel serverless entry point for the VibeX19 website.

The Flask app is created once per lambda instance; environment variables
(Supabase database URL, optional REDIS_URL, DISABLE_SCHEDULER) are set in
the Vercel dashboard, never committed.
"""

import os
import sys

# api/ -> project (website) root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

app = create_app()

from __future__ import annotations

import os


def configure_runtime_environment() -> None:
    """Apply environment fixes needed before importing libraries with global init."""
    if os.getenv("VERCEL") and not os.getenv("DSPY_CACHEDIR"):
        # Vercel's writable filesystem is temporary and exposed under /tmp.
        os.environ["DSPY_CACHEDIR"] = "/tmp/.dspy_cache"


"""
Telekom Private Customer Profiler — usage-driven B2C plan recommendations.

Run::

    python app.py
    python -m telekom_profiler
"""

from telekom_profiler.ui.demo import create_demo, main

__version__ = "0.1.0"
__all__ = ["__version__", "create_demo", "main"]

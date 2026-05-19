"""
Telekom Private Customer Profiler — usage-driven B2C plan recommendations.

Run::

    python app.py
    python -m telekom_profiler

Documentation: ``docs/`` in the repository root. Public service API:
``telekom_profiler.services.profile_customer``, ``ProfilerEngine``.
"""

from telekom_profiler.ui.demo import create_demo, main

__version__ = "0.1.0"
__all__ = ["__version__", "create_demo", "main"]

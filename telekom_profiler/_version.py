"""Package version — set in ``pyproject.toml``; do not edit here manually."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("telekom-personal-plan-recommender")
except PackageNotFoundError:
    # Editable install / running from source without metadata.
    __version__ = "0.0.0+dev"

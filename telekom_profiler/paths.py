"""Package-root paths for assets, data, and prompt templates."""

from pathlib import Path
from typing import Final

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
ASSETS_DIR: Final[Path] = PACKAGE_ROOT / "assets"
DATA_DIR: Final[Path] = PACKAGE_ROOT / "data"
PROMPT_TEMPLATES_DIR: Final[Path] = PACKAGE_ROOT / "prompts" / "templates"
THEME_DIR: Final[Path] = PACKAGE_ROOT / "ui" / "theme"

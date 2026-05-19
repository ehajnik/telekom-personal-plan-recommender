"""Package-root paths for assets, data, and prompt templates."""

from pathlib import Path
from typing import Final

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
REPO_ROOT: Final[Path] = PACKAGE_ROOT.parent
ASSETS_DIR: Final[Path] = PACKAGE_ROOT / "assets"
DATA_DIR: Final[Path] = PACKAGE_ROOT / "data"
RAW_DATA_DIR: Final[Path] = REPO_ROOT / "data" / "raw"
ARTIFACTS_DIR: Final[Path] = REPO_ROOT / "artifacts"
PROMPT_TEMPLATES_DIR: Final[Path] = PACKAGE_ROOT / "prompts" / "templates"
THEME_DIR: Final[Path] = PACKAGE_ROOT / "ui" / "theme"

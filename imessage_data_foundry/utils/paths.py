"""Path utilities for iMessage Data Foundry."""

import os
from pathlib import Path


def get_default_db_path() -> Path:
    """Get the default path for foundry.db."""
    config_path = os.environ.get("IMESSAGE_FOUNDRY_CONFIG")
    if config_path:
        return Path(config_path).parent / "foundry.db"

    xdg_path = Path.home() / ".config" / "imessage-data-foundry" / "foundry.db"
    if xdg_path.parent.exists() or not Path("./data").exists():
        return xdg_path

    return Path("./data/foundry.db")

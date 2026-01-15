import os
from pathlib import Path

from imessage_data_foundry.utils.constants import (
    FOUNDRY_CONFIG_ENV_VAR,
    FOUNDRY_DB_NAME,
)


def get_default_db_path() -> Path:
    config_path = os.environ.get(FOUNDRY_CONFIG_ENV_VAR)
    if config_path:
        return Path(config_path).parent / FOUNDRY_DB_NAME

    xdg_path = Path.home() / ".config" / "imessage-data-foundry" / FOUNDRY_DB_NAME
    if xdg_path.parent.exists() or not Path("./data").exists():
        return xdg_path

    return Path("./data") / FOUNDRY_DB_NAME

import os
from pathlib import Path

APP_DIR = "com.kevincojean/cli-tools-friend"


def data_dir() -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    path = cache / APP_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = config / APP_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_file(name: str) -> Path:
    return data_dir() / name


def config_file() -> Path:
    return config_dir() / "config.json"

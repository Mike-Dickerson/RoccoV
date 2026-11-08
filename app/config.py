import json
import os
from pathlib import Path
from typing import Optional

DATA_DIR = Path(os.getenv("ROCCOV_DATA_DIR", "data"))
AUTH_FILE = DATA_DIR / "auth.json"


def get_api_key() -> Optional[str]:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key
    if AUTH_FILE.exists():
        return json.loads(AUTH_FILE.read_text()).get("openai_api_key")
    return None


def save_api_key(key: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps({"openai_api_key": key}))

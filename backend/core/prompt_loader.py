import hashlib
import os
import re
from functools import lru_cache
from pathlib import Path

PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")

@lru_cache(maxsize=32)
def load_prompt(name: str, version: str = "v1") -> str:
    if not _SAFE_NAME.fullmatch(name) or not _SAFE_NAME.fullmatch(version):
        raise ValueError("prompt 名称和版本只能包含字母、数字、下划线和连字符")
    path = PROMPT_ROOT / name / f"{version}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"prompt 模板不存在: {path}")
    return path.read_text(encoding="utf-8").strip()

def render_prompt(name: str, version: str = "v1", **values) -> str:
    return load_prompt(name, version).format(**values)

def resolve_prompt_version(user_id=None) -> str:
    stable = os.getenv("PROMPT_VERSION", "v1")
    canary = os.getenv("PROMPT_CANARY_VERSION", "").strip()
    if not canary or canary == stable:
        return stable
    forced_users = {item.strip() for item in os.getenv("PROMPT_CANARY_USERS", "").split(",") if item.strip()}
    if user_id is not None and str(user_id) in forced_users:
        return canary
    try:
        percent = float(os.getenv("PROMPT_CANARY_PERCENT", "0"))
    except ValueError as exc:
        raise ValueError("PROMPT_CANARY_PERCENT 必须是0到100之间的数字") from exc
    if not 0 <= percent <= 100:
        raise ValueError("PROMPT_CANARY_PERCENT 必须在0到100之间")
    if percent == 100:
        return canary
    if percent == 0 or user_id is None:
        return stable
    digest = hashlib.sha256(f"{canary}:{user_id}".encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") % 10000
    return canary if bucket < int(percent * 100) else stable

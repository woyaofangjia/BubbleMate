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

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_ROOT = PROJECT_ROOT / "prompts"
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

def _release_path():
    return Path(os.getenv(
        "PROMPT_RELEASE_FILE",
        str(PROJECT_ROOT / "data" / "prompt_release.json"),
    ))

def _env_release():
    return {
        "stable_version": os.getenv("PROMPT_VERSION", "v1"),
        "previous_version": os.getenv("PROMPT_PREVIOUS_VERSION", "v1"),
        "canary_version": os.getenv("PROMPT_CANARY_VERSION", ""),
        "canary_percent": os.getenv("PROMPT_CANARY_PERCENT", "0"),
        "canary_users": os.getenv("PROMPT_CANARY_USERS", ""),
        "revision": 0,
        "updated_at": None,
        "reason": "",
        "source": "env",
    }

def _validate_release(release):
    for key in ("stable_version", "previous_version", "canary_version"):
        release[key] = str(release.get(key) or "").strip()
        value = release[key]
        if value and not _SAFE_NAME.fullmatch(value):
            raise ValueError(f"{key} 只能包含字母、数字、下划线和连字符")
    if not release["stable_version"]:
        raise ValueError("stable_version 不能为空")
    try:
        release["canary_percent"] = float(release.get("canary_percent", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("canary_percent 必须是0到100之间的数字") from exc
    if not 0 <= release["canary_percent"] <= 100:
        raise ValueError("canary_percent 必须在0到100之间")
    users = release.get("canary_users", [])
    if isinstance(users, str):
        users = users.split(",")
    release["canary_users"] = [str(item).strip() for item in users if str(item).strip()]
    release["revision"] = int(release.get("revision", 0))
    return release

def get_prompt_release():
    release = _env_release()
    path = _release_path()
    if path.is_file():
        stored = json.loads(path.read_text(encoding="utf-8"))
        release.update(stored)
        release["source"] = "file"
    return _validate_release(release)

def _registered_versions():
    manifest = yaml.safe_load(
        (PROMPT_ROOT / "intent_classify" / "manifest.yaml").read_text(encoding="utf-8")
    ) or {}
    return {release["version"] for release in manifest.get("releases", [])}

def _write_release(release, reason):
    current = get_prompt_release()
    release = _validate_release(release)
    registered_versions = _registered_versions()
    for version in (
        release["stable_version"],
        release["previous_version"],
        release["canary_version"],
    ):
        if version:
            load_prompt("intent_classify", version)
            if version not in registered_versions:
                raise ValueError(f"prompt 版本未登记到 manifest: {version}")
    release.update({
        "revision": current["revision"] + 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "source": "file",
    })
    path = _release_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(release, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return release

def activate_prompt(version, previous_version=None):
    current = get_prompt_release()
    return _write_release({
        "stable_version": version,
        "previous_version": previous_version or current["stable_version"],
        "canary_version": "",
        "canary_percent": 0,
        "canary_users": [],
    }, f"发布稳定版 {version}")

def configure_prompt_canary(version, percent=0, users=None):
    current = get_prompt_release()
    return _write_release({
        "stable_version": current["stable_version"],
        "previous_version": current["previous_version"],
        "canary_version": version,
        "canary_percent": percent,
        "canary_users": users or [],
    }, f"配置灰度版 {version}")

def rollback_prompt():
    current = get_prompt_release()
    canary_active = current["canary_version"] and (
        current["canary_percent"] > 0 or current["canary_users"]
    )
    if canary_active:
        release = _write_release({
            "stable_version": current["stable_version"],
            "previous_version": current["previous_version"],
            "canary_version": "",
            "canary_percent": 0,
            "canary_users": [],
        }, f"回滚灰度版 {current['canary_version']}")
        release.update({
            "action": "disable_canary",
            "from_version": current["canary_version"],
            "to_version": current["stable_version"],
        })
        return release
    previous = current["previous_version"]
    if not previous or previous == current["stable_version"]:
        raise ValueError("没有可回滚的上一版本")
    release = _write_release({
        "stable_version": previous,
        "previous_version": current["stable_version"],
        "canary_version": "",
        "canary_percent": 0,
        "canary_users": [],
    }, f"回滚稳定版 {current['stable_version']} 到 {previous}")
    release.update({
        "action": "rollback_stable",
        "from_version": current["stable_version"],
        "to_version": previous,
    })
    return release

def resolve_prompt_version(user_id=None) -> str:
    release = get_prompt_release()
    stable = release["stable_version"]
    canary = release["canary_version"]
    if not canary or canary == stable:
        return stable
    if user_id is not None and str(user_id) in release["canary_users"]:
        return canary
    percent = release["canary_percent"]
    if percent == 100:
        return canary
    if percent == 0 or user_id is None:
        return stable
    digest = hashlib.sha256(f"{canary}:{user_id}".encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") % 10000
    return canary if bucket < int(percent * 100) else stable

def get_prompt_cache_namespace(prompt_version):
    return f"{prompt_version}@{get_prompt_release()['revision']}"

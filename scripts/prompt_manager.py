import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.cache import cache
from backend.core.prompt_loader import (
    activate_prompt,
    configure_prompt_canary,
    get_prompt_release,
    rollback_prompt,
)

REQUIRED_FIELDS = {"version", "author", "date", "model", "change_reason"}


def generate_changelog():
    sections = ["# Prompt Changelog", "", "<!-- 由 scripts/prompt_manager.py 自动生成，请勿手改。 -->", ""]
    manifests = sorted((PROJECT_ROOT / "prompts").glob("*/manifest.yaml"))
    if not manifests:
        raise ValueError("未找到 prompt manifest")
    for manifest_path in manifests:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        releases = manifest.get("releases", [])
        if not releases:
            raise ValueError(f"{manifest_path} 缺少 releases")
        versions = {release.get("version") for release in releases}
        if manifest.get("version") not in versions:
            raise ValueError(f"{manifest_path} 当前 version 不在 releases 中")
        sections.extend([f"## {manifest_path.parent.name}", ""])
        ordered = sorted(releases, key=lambda item: (str(item["date"]), item["version"]), reverse=True)
        for release in ordered:
            missing = REQUIRED_FIELDS - set(release)
            if missing:
                raise ValueError(f"{manifest_path} 缺少字段: {sorted(missing)}")
            version = release["version"]
            template = manifest_path.parent / f"{version}.txt"
            if not template.is_file():
                raise FileNotFoundError(f"prompt 模板不存在: {template}")
            sections.extend([
                f"### {version} — {release['date']}",
                "",
                f"- 作者：{release['author']}",
                f"- 模型：{release['model']}",
                f"- 变更：{release['change_reason']}",
                "",
            ])
    return "\n".join(sections).rstrip() + "\n"


def write_or_check_changelog(output, check):
    content = generate_changelog()
    if check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            raise ValueError(f"changelog 未更新: {output}；请运行 python scripts/prompt_manager.py changelog")
        print(f"changelog 校验通过: {output}")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"changelog 已生成: {output}")


def clear_prompt_caches():
    cache.clear("intent")
    cache.clear("response")


def main():
    parser = argparse.ArgumentParser(description="BubbleMate prompt 独立发布管理")
    subparsers = parser.add_subparsers(dest="command", required=True)
    changelog = subparsers.add_parser("changelog", help="从 manifest 生成或校验 changelog")
    changelog.add_argument("--output", type=Path, default=PROJECT_ROOT / "prompts" / "CHANGELOG.md")
    changelog.add_argument("--check", action="store_true")
    activate = subparsers.add_parser("activate", help="发布稳定版并停用灰度")
    activate.add_argument("version")
    activate.add_argument("--previous", dest="previous_version")
    canary = subparsers.add_parser("canary", help="配置灰度版本")
    canary.add_argument("version")
    canary.add_argument("--percent", type=float, default=0)
    canary.add_argument("--users", nargs="*", default=[])
    subparsers.add_parser("rollback", help="一键回滚灰度版或上一稳定版")
    subparsers.add_parser("status", help="查看发布状态")
    args = parser.parse_args()

    try:
        if args.command == "changelog":
            write_or_check_changelog(args.output, args.check)
            return
        if args.command == "activate":
            write_or_check_changelog(PROJECT_ROOT / "prompts" / "CHANGELOG.md", True)
            result = activate_prompt(args.version, args.previous_version)
        elif args.command == "canary":
            write_or_check_changelog(PROJECT_ROOT / "prompts" / "CHANGELOG.md", True)
            result = configure_prompt_canary(args.version, args.percent, args.users)
        elif args.command == "rollback":
            result = rollback_prompt()
        else:
            result = get_prompt_release()
        if args.command in {"activate", "canary", "rollback"}:
            clear_prompt_caches()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

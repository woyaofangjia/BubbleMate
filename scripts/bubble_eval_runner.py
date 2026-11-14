import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="后台综合评测入口")
    parser.add_argument("--output", default=str(ROOT / "data" / "eval_report.json"))
    args = parser.parse_args()
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_comprehensive_eval.py")], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    source = ROOT / "reports" / "eval_report.json"
    if not source.is_file():
        raise SystemExit("综合评测未生成 reports/eval_report.json")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)
    print(f"后台评测报告已保存: {output}")


if __name__ == "__main__":
    main()

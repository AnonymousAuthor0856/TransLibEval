#!/usr/bin/env python3
"""
Utility CLI for TransLibEval.

Usage examples:
  python scripts/translib.py env
  python scripts/translib.py test --targets python cpp
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

from translib import load_env_file
from translib.env import get_env
from translib.testing import run_cpp_pipeline, run_python_pipeline, StageResult

ROOT = Path(__file__).resolve().parents[1]


def _format_value(value: str | None, show: bool) -> str:
    if not value:
        return "未设置"
    if not show:
        return "已设置"
    if len(value) <= 6:
        return value
    return f"{value[:3]}...{value[-2:]}"


def command_env(args: argparse.Namespace) -> None:
    load_env_file()
    groups = {
        "OpenAI/GPT": ["OPENAI_API_KEY", "OPENAI_BASE_URL"],
        "Qwen DashScope": ["QWEN_API_KEY", "QWEN_API_BASE"],
        "DeepSeek Qianfan REST": ["DEEPSEEK_API_KEY"],
        "Baidu Qianfan SDK": ["QIANFAN_ACCESS_KEY", "QIANFAN_SECRET_KEY"],
        "Google Custom Search": ["GOOGLE_CSE_ID", "GOOGLE_CSE_API_KEYS"],
    }
    print("当前环境变量状态：")
    for group, keys in groups.items():
        print(f"\n[{group}]")
        for key in keys:
            value = get_env(key)
            rendered = _format_value(value, args.show_values)
            print(f"  {key:<22} {rendered}")
    print(
        "\n提示：可复制 .env.example -> .env 并运行 `python scripts/translib.py env` 以快速检查配置。"
    )


def _print_stage_group(title: str, results: Iterable[StageResult]) -> None:
    print(f"\n{title}")
    for stage in results:
        if stage.skipped:
            print(f"- {stage.name}: ⚠️  跳过（{stage.reason}）")
            continue
        icon = "✅" if stage.success else "❌"
        print(f"- {stage.name}: {icon}  {stage.duration:.1f}s")
        if not stage.success:
            print("  ↳ 请查看上方命令输出定位问题。")


def command_test(args: argparse.Namespace) -> None:
    load_env_file()
    targets = args.targets or ["python", "cpp"]
    if "python" in targets:
        py_summary = run_python_pipeline(args.python_sources)
        for source, stages in py_summary.items():
            title = f"Python 单测（{source} → python）"
            _print_stage_group(title, stages)
    if "cpp" in targets:
        cpp_results = run_cpp_pipeline()
        _print_stage_group("C++ 测试套件", cpp_results)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TransLibEval 辅助脚本")
    sub = parser.add_subparsers(dest="command", required=True)

    env_parser = sub.add_parser("env", help="检查 .env 配置状态")
    env_parser.add_argument(
        "--show-values",
        action="store_true",
        help="在终端中直接显示变量内容（默认仅提示是否已设置）",
    )
    env_parser.set_defaults(func=command_env)

    test_parser = sub.add_parser("test", help="一键运行测试流水线")
    test_parser.add_argument(
        "--targets",
        nargs="+",
        choices=["python", "cpp"],
        default=["python", "cpp"],
        help="选择需要运行的测试平台",
    )
    test_parser.add_argument(
        "--python-sources",
        nargs="+",
        choices=["java", "cpp"],
        default=["java", "cpp"],
        help="当目标语言为 Python 时需要验证的源语言",
    )
    test_parser.set_defaults(func=command_test)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

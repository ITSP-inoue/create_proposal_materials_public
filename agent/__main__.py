"""CLI: python -m agent [--docs-dir DIR] [INPUT.txt]（省略時は標準入力）"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openai import AuthenticationError, RateLimitError

from agent.pipeline import PipelineContext, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="自由記述テキストから提案資料用 Markdown を生成（OpenAI API）",
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="入力テキストファイル（省略時は標準入力）",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Markdown 出力先（既定: docs）",
    )
    args = parser.parse_args()

    if args.input is not None:
        raw = args.input.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        print("入力が空です。ファイルを指定するかパイプで渡してください。", file=sys.stderr)
        sys.exit(1)

    docs_dir = args.docs_dir.resolve()
    if not docs_dir.is_dir():
        print(f"出力先がディレクトリではありません: {docs_dir}", file=sys.stderr)
        sys.exit(1)

    ctx = PipelineContext(raw_input=raw, output_docs_dir=docs_dir)
    try:
        run_pipeline(ctx)
    except RateLimitError as e:
        print(
            "OpenAI API が 429 を返しました（レート制限、またはクレジット・利用枠の不足）。\n"
            "対処: https://platform.openai.com で Billing / Usage を確認し、"
            "プラン・残高・API キーの権限を確認してください。",
            file=sys.stderr,
        )
        print(f"詳細: {e}", file=sys.stderr)
        sys.exit(1)
    except AuthenticationError as e:
        print(
            "OpenAI API の認証に失敗しました（OPENAI_API_KEY が無効、または期限切れの可能性）。",
            file=sys.stderr,
        )
        print(f"詳細: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"生成完了: {docs_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()

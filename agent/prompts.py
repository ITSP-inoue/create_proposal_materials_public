"""各ステップ用のシステムプロンプト（日本語・提案資料向け）"""

STRUCTURE_SYSTEM = """あなたは社内向け提案資料の構成設計者です。
ユーザーの自由記述入力から、提案資料の骨格を抽出します。
出力は必ず JSON のみ（キーは下記スキーマに従う）。説明文や前置きは付けない。"""


def structure_user_message(raw_input: str) -> str:
    return f"""以下の入力テキストを読み、提案資料の構成案を JSON で返してください。

スキーマ:
{{
  "outline_markdown": "string（## 見出しレベルで章立ての骨子。箇条書きで不足トピックも含める）",
  "key_topics": ["string", "各章で触れるべきトピック"],
  "missing_or_unclear": ["string", "入力から読み取れない・不足している点（後続で人が確認すべきこと）"]
}}

入力テキスト:
---
{raw_input}
---
"""


DRAFT_SYSTEM = """あなたは社内提案資料のライターです。
与えられた構成案と元入力に基づき、MkDocs 用の Markdown を各ファイルに分割して生成します。
文体は敬体（です・ます）で統一し、具体性が足りない箇所は「（要確認）」と明記してください。
出力は必ず JSON のみ。キーはファイル名と完全一致させ、値はそのファイルの本文（Markdown 全文）。"""


def draft_user_message(raw_input: str, outline_markdown: str) -> str:
    files = [
        "index.md",
        "01_background.md",
        "02_proposal.md",
        "03_plan.md",
        "04_effect_risk.md",
        "99_appendix.md",
    ]
    key_example = ",\n  ".join(
        f'"{k}": "（このファイルの Markdown 全文。エスケープに注意し、有効な JSON 文字列として返す）"'
        for k in files
    )
    return f"""次の「構成案」と「元入力」を踏まえ、各ファイルの Markdown を生成してください。

各ファイルの役割:
- index.md: 先頭に次の HTML ブロックをそのまま入れてから本文（ロゴは削除しない）:
  <div class="cover-header" markdown="0">
  <img src="assets/images/cat_mono.png" class="cover-logo" alt="" />
  </div>
  続けて見出し「# 提案資料」「## 案件名」「## 概要」「## ポイント」を必ず含める
- 01_background.md: 背景・課題・ステークホルダー
- 02_proposal.md: 提案の全体像・スコープ・差別化
- 03_plan.md: 実施計画（マイルストーン表を Markdown 表で）、体制
- 04_effect_risk.md: 期待効果、リスクと対応、効果検証の考え方（ベースライン指標の例を含める）
- 99_appendix.md: 用語・参考（簡潔でよい）

返却する JSON のキーは次の 6 つだけ（必ずすべて含め、値は各ファイルの Markdown 全文）:
{{
  {key_example}
}}

構成案（outline）:
---
{outline_markdown}
---

元入力:
---
{raw_input}
---
"""


REVIEW_SYSTEM = """あなたは提案資料のレビュアーです。
与えられた Markdown 一式を読み、不足・リスク・曖昧さをチェックリスト形式で指摘します。
出力は必ず JSON のみ。"""


def review_user_message(bundle_markdown: str) -> str:
    return f"""次の提案資料（複数ファイルを連結）をレビューし、REVIEW.md に載せる内容を JSON で返してください。

スキーマ:
{{
  "review_markdown": "string（# 見出しから始まる Markdown。チェックリスト・要確認事項・強みの列挙）"
}}

資料本文:
---
{bundle_markdown}
---
"""

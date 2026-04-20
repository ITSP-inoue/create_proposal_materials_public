from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI


def get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "環境変数 OPENAI_API_KEY が未設定です。"
            "OpenAI の API キーを設定してから再実行してください。"
        )
    return OpenAI(api_key=api_key)


def get_model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def extract_json_object(text: str) -> dict[str, Any]:
    """```json フェンス付きの応答にも対応して JSON オブジェクトを取り出す"""
    t = text.strip()
    fence = re.match(r"^```(?:json)?\s*\n", t)
    if fence:
        t = t[fence.end() :]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3].rstrip()
    return json.loads(t)


def chat_json(system: str, user: str) -> dict[str, Any]:
    client = get_client()
    model = get_model()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("LLM から空の応答が返りました")
    return extract_json_object(content)



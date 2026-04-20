"""
エージェント層: 構造抽出 → 下書き生成 → 不足指摘（いずれも LLM）
生成物は docs/ 配下の Markdown。人がレビュー・編集してから mkdocs build する想定。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agent.llm_client import chat_json
from agent.prompts import (
    DRAFT_SYSTEM,
    REVIEW_SYSTEM,
    STRUCTURE_SYSTEM,
    draft_user_message,
    review_user_message,
    structure_user_message,
)

DOC_FILES = (
    "index.md",
    "01_background.md",
    "02_proposal.md",
    "03_plan.md",
    "04_effect_risk.md",
    "99_appendix.md",
)


@dataclass
class PipelineContext:
    raw_input: str
    output_docs_dir: Path
    outline_markdown: str = ""
    files_content: dict[str, str] = field(default_factory=dict)


def step_structure_extract(ctx: PipelineContext) -> PipelineContext:
    data = chat_json(STRUCTURE_SYSTEM, structure_user_message(ctx.raw_input))
    ctx.outline_markdown = str(data.get("outline_markdown", "")).strip()
    if not ctx.outline_markdown:
        raise RuntimeError("構造抽出の結果に outline_markdown がありません")
    return ctx


def step_draft_generate(ctx: PipelineContext) -> PipelineContext:
    data = chat_json(
        DRAFT_SYSTEM,
        draft_user_message(ctx.raw_input, ctx.outline_markdown),
    )
    for name in DOC_FILES:
        body = data.get(name)
        if not isinstance(body, str) or not body.strip():
            raise RuntimeError(f"下書き生成で {name} が欠落または空です")
        ctx.files_content[name] = body.strip()
    for name, body in ctx.files_content.items():
        path = ctx.output_docs_dir / name
        path.write_text(body + "\n", encoding="utf-8")
    return ctx


def step_gap_review(ctx: PipelineContext) -> PipelineContext:
    bundle = "\n\n---\n\n".join(
        f"## FILE: {name}\n\n{ctx.files_content[name]}" for name in DOC_FILES
    )
    data = chat_json(REVIEW_SYSTEM, review_user_message(bundle))
    review_md = str(data.get("review_markdown", "")).strip()
    if not review_md:
        raise RuntimeError("レビュー結果に review_markdown がありません")
    review_path = ctx.output_docs_dir / "REVIEW.md"
    review_path.write_text(review_md + "\n", encoding="utf-8")
    return ctx


STEP_ORDER = (
    step_structure_extract,
    step_draft_generate,
    step_gap_review,
)


def run_pipeline(ctx: PipelineContext) -> PipelineContext:
    for step in STEP_ORDER:
        ctx = step(ctx)
    return ctx

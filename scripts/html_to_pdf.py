#!/usr/bin/env python3
"""
MkDocs が出力した site/ 以下の HTML を PDF にまとめる。
WeasyPrint を利用。--single-document では全ページを1 HTML に統合してから PDF 化し、
章間リンクが結合 PDF 内で機能するように id / href を調整する。
--all は従来どおり各 HTML を PDF 化して pypdf で結合（リンクは壊れやすい）。
"""
from __future__ import annotations

import argparse
import sys
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

try:
    from bs4 import BeautifulSoup
    from pypdf import PdfReader, PdfWriter
    from weasyprint import HTML
except ImportError as e:
    print(
        "依存パッケージが必要です: pip install weasyprint pypdf beautifulsoup4",
        file=sys.stderr,
    )
    print(e, file=sys.stderr)
    sys.exit(1)

# mkdocs.yml の nav 順（use_directory_urls 既定: 各ページは <slug>/index.html）
DEFAULT_MERGE_PAGES = (
    "index.html",
    "01_background/index.html",
    "02_proposal/index.html",
    "03_plan/index.html",
    "04_effect_risk/index.html",
    "99_appendix/index.html",
)

COMBINED_HTML_NAME = "_pdf_combined.html"


def _rel_to_slug(rel: str) -> str:
    p = Path(rel)
    if p.name == "index.html":
        parent = p.parent.name
        return parent if parent else "index"
    return p.stem


def _path_to_slug(url_path: str) -> str:
    path = unquote(url_path).strip("/")
    if not path or path == "index.html":
        return "index"
    segments = [s for s in path.split("/") if s]
    if not segments:
        return "index"
    last = segments[-1]
    if last == "index.html" and len(segments) >= 2:
        return segments[-2]
    if last == "index.html":
        return "index"
    if last.endswith(".html"):
        return last[:-5]
    return last


def _is_static_asset_path(url_path: str) -> bool:
    p = unquote(url_path).lower()
    if "/assets/" in p or p.startswith("assets/"):
        return True
    return p.endswith(
        (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".woff2", ".woff"),
    )


def _normalize_href_for_root(current_rel: str, href: str) -> str | None:
    """サブページ内の相対パスを site 直下からのパスに直す（アセット用）。"""
    joined = urljoin(f"http://dummy.local/{current_rel}", href)
    parsed = urlparse(joined)
    path = unquote(parsed.path)
    if not _is_static_asset_path(path):
        return None
    return path.lstrip("/")


def _rewrite_links_and_ids(fragment: BeautifulSoup, current_rel: str) -> None:
    slug = _rel_to_slug(current_rel)
    prefix = f"pdf--{slug}--"

    for el in fragment.find_all(id=True):
        old = el.get("id")
        if old:
            el["id"] = prefix + old

    for a in fragment.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("http://", "https://", "mailto:", "javascript:")):
            continue

        norm = _normalize_href_for_root(current_rel, href)
        if norm is not None:
            a["href"] = norm
            continue

        if href.startswith("#"):
            frag = href[1:]
            a["href"] = f"#{prefix}{frag}" if frag else f"#pdf--{slug}"
            continue

        joined = urljoin(f"http://dummy.local/{current_rel}", href)
        parsed = urlparse(joined)
        path = unquote(parsed.path)

        if _is_static_asset_path(path):
            a["href"] = path.lstrip("/")
            continue

        if "/search" in path:
            continue

        target = _path_to_slug(path)
        anchor = parsed.fragment
        if anchor:
            a["href"] = f"#pdf--{target}--{anchor}"
        else:
            a["href"] = f"#pdf--{target}"


def build_combined_html(site_dir: Path, rels: tuple[str, ...]) -> Path:
    """index.html をシェルに、各ページの article 本文を結合した HTML を site 直下に書き出す。"""
    shell = site_dir / rels[0]
    if not shell.is_file():
        raise FileNotFoundError(shell)

    soup = BeautifulSoup(shell.read_text(encoding="utf-8"), "html.parser")
    article = soup.select_one("article.md-content__inner")
    if article is None:
        article = soup.select_one("article")
    if article is None:
        raise RuntimeError("article.md-content__inner または article が見つかりません")

    article.clear()

    for rel in rels:
        page_path = site_dir / rel
        page_soup = BeautifulSoup(page_path.read_text(encoding="utf-8"), "html.parser")
        inner = page_soup.select_one("article.md-content__inner")
        if inner is None:
            inner = page_soup.select_one("article")
        if inner is None:
            raise RuntimeError(f"{rel}: article が見つかりません")

        slug = _rel_to_slug(rel)
        raw_inner = inner.decode_contents()
        wrapped = BeautifulSoup(
            f'<div class="pdf-chapter-body">{raw_inner}</div>',
            "html.parser",
        )
        body_div = wrapped.find("div", class_="pdf-chapter-body")
        if body_div is None:
            raise RuntimeError(f"{rel}: 本文のラップに失敗しました")
        _rewrite_links_and_ids(body_div, rel)

        section = soup.new_tag("section")
        section["class"] = "pdf-chapter"
        section["id"] = f"pdf--{slug}"
        section.append(body_div)
        article.append(section)

    out = site_dir / COMBINED_HTML_NAME
    out.write_text(str(soup), encoding="utf-8")
    return out


def _html_to_pdf_bytes(base: Path, rel: str) -> bytes:
    path = base / rel
    buf = BytesIO()
    HTML(filename=str(path), base_url=str(base) + "/").write_pdf(buf)
    return buf.getvalue()


def _merge_pdfs(parts: list[bytes], output: Path) -> None:
    writer = PdfWriter()
    for data in parts:
        reader = PdfReader(BytesIO(data))
        for page in reader.pages:
            writer.add_page(page)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as f:
        writer.write(f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MkDocs の site から HTML を PDF 化",
    )
    parser.add_argument(
        "--site-dir",
        type=Path,
        default=Path("site"),
        help="mkdocs build の出力ディレクトリ",
    )
    parser.add_argument(
        "--single-document",
        action="store_true",
        help="全ページを1 HTML にまとめてから PDF 化（章間リンクを維持しやすい）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="nav 順に各 HTML を PDF 化し pypdf で結合（--single-document より優先しない）",
    )
    parser.add_argument(
        "--entry",
        default="index.html",
        help="単一 PDF 化する HTML（site 直下の相対パス。他モード未指定時）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("dist/proposal.pdf"),
        help="出力 PDF パス",
    )
    args = parser.parse_args()

    base = args.site_dir.resolve()
    if not base.is_dir():
        print(f"site がありません: {base}", file=sys.stderr)
        sys.exit(1)

    if args.single_document:
        rels = tuple(DEFAULT_MERGE_PAGES)
        missing = [r for r in rels if not (base / r).is_file()]
        if missing:
            print("次の HTML が見つかりません（mkdocs build を実行済みか確認）:", file=sys.stderr)
            for m in missing:
                print(f"  - {m}", file=sys.stderr)
            sys.exit(1)
        try:
            combined = build_combined_html(base, rels)
        except (OSError, RuntimeError) as e:
            print(f"単一 HTML の生成に失敗: {e}", file=sys.stderr)
            sys.exit(1)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        HTML(
            filename=str(combined),
            base_url=str(base) + "/",
        ).write_pdf(args.output)
        print(
            f"PDF 出力（単一 HTML: {combined.name}）: {args.output.resolve()}",
            file=sys.stderr,
        )
        return

    if args.all:
        rels = list(DEFAULT_MERGE_PAGES)
        missing = [r for r in rels if not (base / r).is_file()]
        if missing:
            print("次の HTML が見つかりません（mkdocs build を実行済みか確認）:", file=sys.stderr)
            for m in missing:
                print(f"  - {m}", file=sys.stderr)
            sys.exit(1)
        parts = [_html_to_pdf_bytes(base, r) for r in rels]
        _merge_pdfs(parts, args.output)
        print(
            f"PDF 出力（全 {len(rels)} 断片を pypdf 結合）: {args.output.resolve()}",
            file=sys.stderr,
        )
        return

    entry = base / args.entry
    if not entry.is_file():
        print(f"見つかりません: {entry}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    HTML(filename=str(entry), base_url=str(base) + "/").write_pdf(args.output)
    print(f"PDF 出力（単一: {args.entry}）: {args.output.resolve()}", file=sys.stderr)


if __name__ == "__main__":
    main()

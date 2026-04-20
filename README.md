# Proposal Material Generator

- Input text → proposal Markdown
- Build HTML with MkDocs
- Export PDF via Docker

## 環境変数（`.env`）

リポジトリ直下に `.env` ファイルを用意してください。`.gitignore` で除外されているため、各自の環境で作成する必要があります。`docker compose` は同じディレクトリの `.env` を自動読み込みし、`docker-compose.yml` の `${OPENAI_API_KEY}` などに反映されます。

**必要な変数**

- **`OPENAI_API_KEY`**（必須）: OpenAI API キー。`proposal-generate`（Markdown 生成）で使用します。
- **`OPENAI_MODEL`**（任意）: 使用モデル。未設定時は `gpt-4o-mini`（`docker-compose.yml` の既定値と一致）。

**例（`.env`）**

```env
OPENAI_API_KEY=sk-...your-key...
OPENAI_MODEL=gpt-4o-mini
```

`.env` を使わない場合は、`docker compose run` に `-e OPENAI_API_KEY=...` を付けて実行時に渡すこともできます。

## Quick Start

```bash
docker compose build
docker compose run --rm -v "${PWD}/input.txt:/app/input.txt:ro" proposal-generate /app/input.txt
docker compose run --rm proposal-build
```

`proposal-build` は `mkdocs build` で **`site/` に静的サイトを生成**してから PDF を出力します。`docker-compose.yml` で **`./site` と `./dist` をコンテナにマウント**しているため、実行後はプロジェクト直下に `site/` と `dist/` ができます（いずれも `.gitignore` 済みでリポジトリには含みません）。**エクスプローラーで見えても IDE のファイル一覧では `site/` が非表示になることがあります**（`.gitignore` 対象を隠す設定のため）。確認はエクスプローラーや `dir site`（PowerShell）で行ってください。PDF では [`docs/assets/css/custom.css`](docs/assets/css/custom.css) の **`@media print`** により、ヘッダー・サイドバーなどを省いた体裁になります。

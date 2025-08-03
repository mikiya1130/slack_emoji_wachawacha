# 開発に必要なコマンド集

## Docker Compose コマンド
```bash
# 環境の起動
docker-compose up -d --build

# ログ確認
docker-compose logs -f app

# コンテナ内でコマンド実行
docker compose exec app <command>

# 環境の停止
docker-compose down
```

## テスト実行
```bash
# 全テスト実行（Docker内）
docker compose exec app pytest

# カバレッジ付きテスト
docker compose exec app pytest --cov=app --cov-report=term-missing

# 特定のテストファイル実行
docker compose exec app pytest tests/test_services/test_openai_service.py

# テストマーカー指定
docker compose exec app pytest -m unit
```

## コード品質チェック（必須実行順）
```bash
# 1. コードフォーマット
docker compose exec app black app/ tests/

# 2. Lintチェック
docker compose exec app flake8 app/ tests/

# 3. 型チェック
docker compose exec app mypy app/

# 4. テスト実行（カバレッジ付き）
docker compose exec app pytest --cov=app --cov-report=term-missing
```

## データベース操作
```bash
# pgwebでGUI表示
http://localhost:8081

# psqlでアクセス
docker compose exec db psql -U user -d emoji_bot
```

## Git操作
```bash
git status
git diff
git add .
git commit -m "feat: スラッシュコマンド機能実装"
git log --oneline -10
```
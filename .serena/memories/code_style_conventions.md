# コードスタイルとコンベンション

## Python コーディング規約
- **PEP 8準拠**: Blackでフォーマット（最大行長100文字）
- **型ヒント必須**: すべての関数に型アノテーション
- **Docstring**: 各クラス・メソッドに説明文（日本語可）

## ネーミング規則
- クラス名: PascalCase（例: `SlackHandler`）
- 関数・変数名: snake_case（例: `handle_message`）
- 定数: UPPER_SNAKE_CASE（例: `DEFAULT_MAX_RETRIES`）
- プライベートメソッド: アンダースコア接頭辞（例: `_sanitize_emoji_name`）

## ディレクトリ構造
```
app/
├── services/     # ビジネスロジック
├── models/       # データモデル
├── utils/        # ユーティリティ
└── config.py     # 設定管理

tests/
├── test_services/  # サービステスト
├── fixtures/       # テストデータ
└── conftest.py     # pytest設定
```

## 非同期処理
- すべてのSlackハンドラーは`async def`
- データベース操作も非同期（`asyncpg`使用）
- `asyncio.gather`で並行処理

## エラーハンドリング
- カスタム例外クラスを使用（`ApplicationError`継承）
- Circuit Breaker パターンでサービス保護
- 詳細なログ出力（構造化ログ）

## テスト規約
- TDD厳守：RED → GREEN → REFACTOR
- モックは`pytest-mock`使用
- フィクスチャは`conftest.py`に集約
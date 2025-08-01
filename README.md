# Slack絵文字リアクションBot

RAG（Retrieval-Augmented Generation）とベクトル類似度検索を用いて、メッセージに文脈に適した絵文字リアクションを自動的に追加するSlackボットです。

## 機能

- **自動絵文字リアクション**: メッセージ内容を分析して関連する絵文字リアクションを追加
- **RAG実装**: OpenAI埋め込みとpgvectorを使ったPostgreSQLによる類似度検索
- **Socket Mode**: SlackのSocket Modeによるリアルタイムメッセージ処理
- **Docker環境**: PostgreSQL + pgvectorデータベースを含むコンテナ化されたアプリケーション
- **TDDアプローチ**: 包括的なテストカバレッジを伴うテスト駆動開発

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose環境                        │
│                                                           │
│  ┌─────────────────────┐      ┌─────────────────────────┐  │
│  │    app コンテナ        │      │     db コンテナ         │  │
│  │                     │      │                         │  │
│  │  ┌───────────────┐  │      │  ┌─────────────────┐    │  │
│  │  │  Slack Bolt   │◄─┼──────┼─►│  PostgreSQL     │    │  │
│  │  │   Framework   │  │      │  │   + pgvector    │    │  │
│  │  │ (Socket Mode) │  │      │  └─────────────────┘    │  │
│  │  └───────────────┘  │      │                         │  │
│  │                     │      │  ┌─────────────────┐    │  │
│  │  ┌───────────────┐  │      │  │  Vector Store   │    │  │
│  │  │  OpenAI SDK   │  │      │  │  (Emoji Data)   │    │  │
│  │  │(text-embedding│  │      │  └─────────────────┘    │  │
│  │  │  -3-small)    │  │      │                         │  │
│  │  └───────────────┘  │      └─────────────────────────┘  │
│  └─────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
```

## 技術スタック

- **言語**: Python 3.12+
- **Slack SDK**: slack-bolt-python (Socket Mode)
- **データベース**: PostgreSQL 16+ with pgvector拡張
- **DBクライアント**: psycopg3
- **AIモデル**: OpenAI "text-embedding-3-small"
- **コンテナ化**: Docker & Docker Compose
- **テスト**: pytest（非同期サポート、80%以上のカバレッジ要件）

## セットアップ

### 前提条件

- Docker and Docker Compose
- Socket Mode対応のSlack App
- OpenAI APIキー

### 環境セットアップ

1. **プロジェクトのクローンと移動**:
   ```bash
   cd slack_emoji_wachawacha
   ```

2. **環境ファイルの作成**:
   ```bash
   cp .env.example .env
   ```

3. **`.env`で環境変数を設定**:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_APP_TOKEN=xapp-your-app-token-here
   OPENAI_API_KEY=sk-your-openai-api-key-here
   ```

### Slack App設定

1. https://api.slack.com/apps で新しいSlack Appを作成
2. Socket Modeを有効化してApp-Level Tokenを生成
3. Bot Token Scopesを追加:
   - `channels:history` - メッセージ読み取り
   - `reactions:write` - 絵文字リアクション追加
4. ワークスペースにアプリをインストールしてBot User OAuth Tokenをコピー

### アプリケーションの実行

1. **データベースの起動**:
   ```bash
   docker-compose up -d db
   ```

2. **アプリケーションの実行**:
   ```bash
   docker-compose up app
   ```

   または両方を同時に実行:
   ```bash
   docker-compose up -d
   ```

3. **ログの確認**:
   ```bash
   docker-compose logs -f app
   ```

### 開発環境セットアップ

1. **Python依存関係のインストール**（ローカル開発用）:
   ```bash
   pip install -r requirements.txt
   ```

2. **テストの実行**:
   ```bash
   pytest
   ```

3. **カバレッジ付きテストの実行**:
   ```bash
   pytest --cov=app --cov-report=html
   ```

4. **コード品質チェック**:
   ```bash
   black app/ tests/     # コードフォーマット
   mypy app/             # 型チェック
   flake8 app/ tests/    # リンティング
   ```

## 開発プロセス

このプロジェクトは**テスト駆動開発（TDD）**に従います：

1. **RED**: 最初に失敗するテストを書く
2. **GREEN**: テストをパスする最小限のコードを実装
3. **REFACTOR**: テストをパスしたまま、コードを改善

### テストカテゴリ

- **単体テスト**: 個々のコンポーネントを分離してテスト
- **統合テスト**: コンポーネント間の相互作用をテスト
- **E2Eテスト**: 完全なワークフローをテスト

### テストマーカー

```bash
pytest -m unit           # 単体テストのみ実行
pytest -m integration    # 統合テストのみ実行
pytest -m "not slow"     # 低速テストをスキップ
```

## プロジェクト構成

```
slack_emoji_wachawacha/
├── app/
│   ├── main.py              # アプリケーションエントリーポイント
│   ├── config.py            # 設定管理
│   ├── services/
│   │   ├── slack_handler.py  # Slack連携
│   │   ├── openai_service.py # OpenAI APIクライアント
│   │   ├── emoji_service.py  # 絵文字管理
│   │   └── database_service.py # データベース操作
│   ├── models/
│   │   └── emoji.py         # データモデル
│   └── utils/
│       └── logging.py       # ログ設定
├── data/
│   └── emojis.json          # 絵文字データファイル
├── tests/
│   ├── test_services/       # サービステスト
│   └── fixtures/            # テストデータ
├── docker-compose.yml       # コンテナオーケストレーション
├── Dockerfile              # アプリコンテナ定義
└── requirements.txt        # Python依存関係
```

## 実装状況

### ✅ Phase 0: 環境構築（完了）
- [x] プロジェクト構造作成
- [x] Docker環境設定
- [x] PostgreSQL + pgvectorデータベースセットアップ
- [x] 基本Python設定とログ機能
- [x] TDDテストインフラ

### 🚧 Phase 1: Slack連携（予定）
- [ ] TDDによるSlackHandler実装
- [ ] Socket Modeメッセージ受信
- [ ] 絵文字リアクション送信
- [ ] メッセージフィルタリング

### 🚧 Phase 2: データベース・絵文字管理（予定）
- [ ] pgvectorを使ったDatabaseService
- [ ] 類似度検索用EmojiService
- [ ] 絵文字データモデル
- [ ] データロードユーティリティ

### 🚧 Phase 3: OpenAI・RAG実装（予定）
- [ ] 埋め込み用OpenAIService
- [ ] ベクトル類似度検索
- [ ] RAG統合
- [ ] エンドツーエンドワークフロー

### 🚧 Phase 4: テスト・品質保証（予定）
- [ ] 包括的テストカバレッジ
- [ ] パフォーマンス最適化
- [ ] エラーハンドリング改善
- [ ] ドキュメント完成

## 設定

### データベーススキーマ

```sql
CREATE TABLE emojis (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,  -- 例: ":smile:"
    description TEXT NOT NULL,          -- 意味の説明
    category VARCHAR(50),               -- 絵文字カテゴリ
    emotion_tone VARCHAR(20),           -- positive/negative/neutral
    usage_scene VARCHAR(100),           -- 使用場面
    priority INTEGER DEFAULT 1,        -- 重み付け係数
    embedding VECTOR(1536),             -- OpenAI埋め込みベクトル
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 環境変数

| 変数 | 説明 | 必須 |
|------|------|------|
| `SLACK_BOT_TOKEN` | Slack Bot User OAuth Token | はい |
| `SLACK_APP_TOKEN` | Slack App-Level Token | はい |
| `OPENAI_API_KEY` | OpenAI API Key | はい |
| `DATABASE_URL` | PostgreSQL接続文字列 | いいえ（デフォルトあり） |
| `ENVIRONMENT` | 環境（development/production） | いいえ（デフォルト: development） |
| `LOG_LEVEL` | ログレベル | いいえ（デフォルト: INFO） |

## 貢献

1. TDDアプローチに従う：テストファースト、その後実装
2. 80%以上のテストカバレッジを維持
3. 提供されたコード品質ツールを使用（black、mypy、flake8）
4. 新機能のドキュメントを更新

## ライセンス

このプロジェクトはTDDベストプラクティスに従った教育目的のものです。
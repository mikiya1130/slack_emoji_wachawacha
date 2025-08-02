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

### ✅ Phase 1: Slack連携（完了）
- [x] TDDによるSlackHandler実装
- [x] Socket Modeメッセージ受信
- [x] 絵文字リアクション送信
- [x] メッセージフィルタリング

### ✅ Phase 2: データベース・絵文字管理（完了）
- [x] pgvectorを使ったDatabaseService
- [x] 類似度検索用EmojiService
- [x] 絵文字データモデル
- [x] データロードユーティリティ

### ✅ Phase 3: OpenAI・RAG実装（完了）
- [x] 埋め込み用OpenAIService
- [x] ベクトル類似度検索
- [x] RAG統合
- [x] エンドツーエンドワークフロー

### ✅ Phase 4: テスト・品質保証（完了）
- [x] 包括的テストカバレッジ（81%達成）
- [x] パフォーマンス最適化
- [x] エラーハンドリング改善
- [x] ドキュメント完成

### ✅ Phase 5: 最終仕上げ（完了）
- [x] エラーハンドリング強化（包括的エラー処理、Circuit Breaker実装）
- [x] 設定管理強化（データクラス化、実行時ロード対応）
- [x] ドキュメント作成（運用手順書、API仕様書）
- [x] 最終動作確認（Code Quality Check完了）

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

## API仕様

### サービスAPI

#### SlackHandler

Slackとの連携を管理するメインハンドラー。

**主要メソッド:**

- `handle_message(message: Dict[str, Any])` - Slackメッセージを処理し、絵文字リアクションを追加
- `add_reactions(channel: str, timestamp: str, emojis: List[str])` - 指定メッセージに絵文字リアクションを追加
- `get_metrics()` - パフォーマンスメトリクスを取得

#### OpenAIService

テキストのベクトル化を担当。

**主要メソッド:**

- `get_embedding(text: str) -> np.ndarray` - テキストを1536次元のベクトルに変換
- `get_embeddings_batch(texts: List[str]) -> List[np.ndarray]` - 複数テキストの一括ベクトル化

#### EmojiService

絵文字データの管理とベクトル検索。

**主要メソッド:**

- `find_similar_emojis(query_vector: List[float], limit: int = 3)` - ベクトル類似度で絵文字を検索
- `search_by_text(text: str, emotion_tone: str = None)` - テキストから直接絵文字を検索（RAG統合）
- `vectorize_all_emojis(skip_existing: bool = True)` - 全絵文字データのベクトル化

#### DatabaseService

PostgreSQL + pgvectorとの連携。

**主要メソッド:**

- `find_similar_emojis(embedding: List[float], limit: int = 3)` - pgvectorを使用したコサイン類似度検索
- `insert_emoji(emoji: EmojiData)` - 絵文字データの挿入（UPSERT）
- `batch_update_embeddings(embedding_updates: Dict[int, List[float]])` - 埋め込みベクトルの一括更新

### エラーハンドリング

```
ApplicationError
├── ConfigurationError    # 設定エラー（CRITICAL）
├── ServiceError         # サービスエラーの基底クラス
│   ├── SlackServiceError   # Slack関連エラー
│   ├── OpenAIServiceError  # OpenAI関連エラー
│   ├── DatabaseError       # データベース関連エラー
│   └── EmojiServiceError   # 絵文字サービスエラー
```

## 運用

### 起動と停止

```bash
# 全サービスの起動
docker-compose up -d

# 特定サービスのみ起動
docker-compose up -d db
docker-compose up -d app

# グレースフルシャットダウン
docker-compose stop

# 再起動
docker-compose restart app
```

### 運用監視

#### ログ監視

```bash
# リアルタイムログ監視
docker-compose logs -f app

# エラーログのみ抽出
docker-compose logs app | grep ERROR
```

#### ヘルスチェック

```bash
# アプリケーションのヘルスチェック
curl http://localhost:8080/health

# メトリクスエンドポイント（Prometheus形式）
curl http://localhost:9090/metrics
```

### トラブルシューティング

#### Slackに接続できない

```bash
# トークンの確認
docker-compose exec app python -c "
from app.config import Config
config = Config()
print(f'Bot Token: {config._mask_sensitive(config.slack.bot_token)}')
print(f'App Token: {config._mask_sensitive(config.slack.app_token)}')
"
```

#### リアクションが追加されない

- ログでエラーを確認: `docker-compose logs app | grep ERROR`
- レート制限の確認: OpenAI/Slack APIのレート制限
- 絵文字データの確認: データベースに絵文字が登録されているか

### メンテナンス

#### バックアップ

```bash
# データベースのバックアップ
docker-compose exec db pg_dump -U postgres emoji_bot > backup_$(date +%Y%m%d).sql

# 設定ファイルのバックアップ
tar czf config_backup_$(date +%Y%m%d).tar.gz .env config/
```

#### アップデート手順

```bash
# 1. 現在の状態をバックアップ
./scripts/backup.sh

# 2. 新バージョンの取得
git pull origin main

# 3. 依存関係の更新
docker-compose build --no-cache

# 4. サービスの再起動
docker-compose down
docker-compose up -d
```

## セキュリティ

### アクセス制御

- 環境変数ファイル（.env）の権限設定: `chmod 600 .env`
- Dockerソケットへのアクセス制限
- データベースの接続元IP制限

### 秘密情報の管理

- API KeysやTokensは環境変数で管理
- 本番環境ではSecret Management Service使用推奨
- ログに秘密情報が出力されないよう注意

### 監査ログ

```bash
# セキュリティ関連イベントの監視
docker-compose logs app | grep -E "(AUTH|SECURITY|ACCESS)"
```

## 貢献

1. TDDアプローチに従う：テストファースト、その後実装
2. 80%以上のテストカバレッジを維持
3. 提供されたコード品質ツールを使用（black、mypy、flake8）
4. 新機能のドキュメントを更新

## ライセンス

このプロジェクトはTDDベストプラクティスに従った教育目的のものです。
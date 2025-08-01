# 詳細設計書 - Slack絵文字リアクションBot

## 1. アーキテクチャ概要

### 1.1 システム構成図

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
│              │                                             │
└──────────────┼─────────────────────────────────────────────┘
               │
               ▼
    ┌─────────────────────┐
    │    Slack API        │
    │   (Socket Mode)     │
    └─────────────────────┘
```

### 1.2 技術スタック

- **言語**: Python 3.12+
- **Slack SDK**: slack-bolt-python (Socket Mode専用)
- **データベース**: PostgreSQL 16+ + pgvector拡張
- **DBクライアント**: psycopg (psycopg3)
- **埋め込みモデル**: OpenAI "text-embedding-3-small"
- **OpenAI SDK**: openai-python (v1.68.0+)
- **コンテナ化**: Docker & Docker Compose
- **主要ライブラリ**:
  - `slack-bolt`: Slack Bot開発フレームワーク
  - `psycopg[binary]`: PostgreSQLクライアント
  - `openai`: OpenAI API クライアント

## 2. コンポーネント設計

### 2.1 コンポーネント一覧

| コンポーネント名 | 責務 | 依存関係 |
|---|---|---|
| SlackHandler | Slackメッセージ受信・リアクション送信 | OpenAIService, EmojiService |
| OpenAIService | メッセージのベクトル化処理 | openai-python |
| EmojiService | 絵文字データ管理・類似度検索 | DatabaseService |
| DatabaseService | PostgreSQL/pgvector操作 | psycopg3 |
| ConfigManager | 環境変数・設定管理 | - |

### 2.2 各コンポーネントの詳細

#### SlackHandler

- **目的**: Slackとの連携を担当する主要コンポーネント
- **公開インターフェース**:
  ```python
  class SlackHandler:
      def __init__(self, openai_service: OpenAIService, emoji_service: EmojiService):
          pass
      
      def handle_message(self, message: dict) -> None:
          """メッセージを受信し、絵文字リアクションを付与"""
          pass
      
      def add_reactions(self, channel: str, timestamp: str, emojis: List[str]) -> None:
          """指定されたメッセージに絵文字リアクションを追加"""
          pass
  ```
- **内部実装方針**: 
  - Slack Bolt FrameworkのSocket Modeを使用
  - メッセージフィルタリング（Bot自身の投稿除外）を実装
  - 非同期処理でリアクション送信のパフォーマンスを確保

#### OpenAIService

- **目的**: OpenAI APIを使用したテキストの埋め込みベクトル化
- **公開インターフェース**:
  ```python
  class OpenAIService:
      def __init__(self, api_key: str):
          pass
      
      async def get_embedding(self, text: str) -> List[float]:
          """テキストをベクトル化"""
          pass
  ```
- **内部実装方針**: 
  - OpenAI Python SDK (v1.68.0+) を使用
  - text-embedding-3-small モデルを使用
  - レート制限とエラーハンドリングを考慮した実装

#### EmojiService

- **目的**: 絵文字データの管理と類似度検索
- **公開インターフェース**:
  ```python
  class EmojiService:
      def __init__(self, db_service: DatabaseService):
          pass
      
      async def find_similar_emojis(self, message_vector: List[float], limit: int = 3) -> List[EmojiData]:
          """類似度の高い絵文字を検索"""
          pass
      
      async def load_emojis_from_file(self, file_path: str) -> None:
          """JSON/CSVファイルから絵文字データを一括登録"""
          pass
  ```
- **内部実装方針**: 
  - pgvectorのコサイン類似度検索を使用
  - 絵文字メタデータ（コード、説明文、カテゴリ、感情トーン、使用シーン、優先度）を管理

#### DatabaseService

- **目的**: PostgreSQL + pgvectorの操作を抽象化
- **公開インターフェース**:
  ```python
  class DatabaseService:
      def __init__(self, connection_string: str):
          pass
      
      async def execute_query(self, query: str, params: tuple = ()) -> Any:
          """SQLクエリの実行"""
          pass
      
      async def vector_similarity_search(self, vector: List[float], table: str, limit: int) -> List[dict]:
          """ベクトル類似度検索"""
          pass
  ```
- **内部実装方針**: 
  - psycopg3 を使用した非同期PostgreSQL接続
  - コネクションプールを使用して効率的なDB接続管理
  - pgvector 拡張を使用したベクトル検索

## 3. データフロー

### 3.1 データフロー図

```
Slackメッセージ受信
        │
        ▼
  [SlackHandler]
   メッセージフィルタリング
        │
        ▼
  [OpenAIService]
   メッセージベクトル化
        │
        ▼
  [EmojiService]
   類似度検索（上位3個）
        │
        ▼
  [SlackHandler]
   絵文字リアクション送信
        │
        ▼
   Slack チャンネル
```

### 3.2 データ変換

- **入力データ形式**: Slack メッセージイベント（JSON）
  ```json
  {
    "type": "message",
    "text": "今日はいい天気ですね！",
    "user": "U123456789",
    "channel": "C123456789",
    "ts": "1234567890.123456"
  }
  ```

- **処理過程**: 
  1. メッセージテキストを抽出
  2. OpenAI APIでベクトル化（1536次元）
  3. pgvectorでコサイン類似度検索
  4. 上位3個の絵文字を選定

- **出力データ形式**: 絵文字リアクション
  ```python
  reactions = [":smile:", ":sunny:", ":thumbsup:"]
  ```

## 4. データベース設計

### 4.1 テーブル設計

#### emojis テーブル
```sql
CREATE TABLE emojis (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,  -- 例: ":smile:"
    description TEXT NOT NULL,          -- 説明文
    category VARCHAR(50),               -- カテゴリ（感情、行動、物など）
    emotion_tone VARCHAR(20),           -- ポジティブ/ネガティブ/ニュートラル
    usage_scene VARCHAR(100),           -- 使用シーン
    priority INTEGER DEFAULT 1,        -- 優先度/重み
    embedding VECTOR(1536),             -- OpenAI埋め込みベクトル
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ベクトル検索用インデックス
CREATE INDEX ON emojis USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## 5. APIインターフェース

### 5.1 内部API

- **SlackHandler ↔ OpenAIService**
  ```python
  embedding = await openai_service.get_embedding(message_text)
  ```

- **SlackHandler ↔ EmojiService**
  ```python
  similar_emojis = await emoji_service.find_similar_emojis(embedding, limit=3)
  ```

### 5.2 外部API

- **Slack API (受信)**
  - Socket Mode: WebSocket接続

- **Slack API (送信)**
  - `reactions.add`: 絵文字リアクション追加

- **OpenAI API**
  - `embeddings.create`: テキスト埋め込み生成


## 6. エラーハンドリング

### 6.1 エラー分類

- **OpenAI API エラー**
  - レート制限エラー → リトライ処理
  - 認証エラー → ログ出力・処理停止
  - 一時的な障害 → 指数バックオフリトライ

- **Slack API エラー**
  - メッセージ送信失敗 → ログ出力・処理継続
  - 認証エラー → ログ出力・処理停止

- **データベースエラー**
  - 接続エラー → リトライ処理
  - クエリエラー → ログ出力・処理継続

### 6.2 エラー通知

```python
import logging

logger = logging.getLogger(__name__)

try:
    # 処理実行
    pass
except OpenAIError as e:
    logger.error(f"OpenAI API error: {e}")
except SlackAPIError as e:
    logger.error(f"Slack API error: {e}")
except DatabaseError as e:
    logger.error(f"Database error: {e}")
```

## 7. セキュリティ設計

### 7.1 認証・認可

- **Slack App認証**: OAuth 2.0 トークンベース認証
- **OpenAI API**: APIキーベース認証

### 7.2 データ保護

- **環境変数管理**: 
  - `SLACK_BOT_TOKEN`: Slack Bot トークン
  - `SLACK_APP_TOKEN`: Slack App トークン  
  - `OPENAI_API_KEY`: OpenAI API キー
  - `DATABASE_URL`: PostgreSQL 接続文字列

- **個人情報保護**: メッセージ内容は一時処理のみ、永続化しない

## 8. テスト戦略

### 8.1 単体テスト

- **カバレッジ目標**: 80%以上
- **テストフレームワーク**: pytest + pytest-asyncio
- **テスト対象**:
  - `OpenAIService.get_embedding()`
  - `EmojiService.find_similar_emojis()`
  - `DatabaseService` の各メソッド

### 8.2 統合テスト

- **モックテスト**: Slack API, OpenAI API のモック化
- **データベーステスト**: テスト用PostgreSQLコンテナを使用
- **エンドツーエンドテスト**: 実際のSlackメッセージから絵文字リアクションまでの流れ

## 9. パフォーマンス最適化

### 9.1 想定される負荷

- 現時点では考慮不要（元要件に準拠）
- 将来的な目標値:
  - メッセージ受信から絵文字リアクションまで5秒以内
  - 同時メッセージ処理：10件/分
  - ベクトル検索応答時間：1秒以内

### 9.2 最適化方針

- **非同期処理**: asyncio を使用した非ブロッキング処理
- **データベース**: pgvector インデックスによる高速ベクトル検索
- **キャッシュ**: 頻繁に使用される絵文字のベクトルをメモリキャッシュ

## 10. デプロイメント

### 10.1 デプロイ構成

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/emoji_bot
    depends_on:
      - db

  db:
    image: pgvector/pgvector:pg14
    environment:
      - POSTGRES_DB=emoji_bot
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### 10.2 設定管理

- **.env ファイル**: 環境変数の管理
- **config.py**: アプリケーション設定の一元管理
- **Docker環境変数**: コンテナ固有の設定

## 11. ディレクトリ構成

```
slack_emoji_wachawacha/
├── app/
│   ├── __init__.py
│   ├── main.py              # Slack Bolt アプリケーションエントリーポイント
│   ├── config.py            # 設定管理
│   ├── services/
│   │   ├── __init__.py
│   │   ├── slack_handler.py  # SlackHandler
│   │   ├── openai_service.py # OpenAIService
│   │   ├── emoji_service.py  # EmojiService
│   │   └── database_service.py # DatabaseService
│   ├── models/
│   │   ├── __init__.py
│   │   └── emoji.py         # データモデル
│   └── utils/
│       ├── __init__.py
│       └── logging.py       # ログ設定
├── data/
│   └── emojis.json          # 絵文字データファイル
├── tests/
│   ├── __init__.py
│   ├── test_services/
│   │   ├── test_openai_service.py
│   │   ├── test_emoji_service.py
│   │   └── test_database_service.py
│   └── fixtures/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 12. 実装上の注意事項

- **コードのシンプルさ優先**: 過度な抽象化を避け、理解しやすい実装を心がける
- **最小限の実装**: 必要最小限の機能から開始し、段階的に拡張
- **エラーハンドリング**: 外部API呼び出し時の適切な例外処理
- **ログ出力**: 現時点では簡素化、将来的にエラー追跡用で追加
- **テスト**: 主要な処理フローに対する単体テスト・統合テストの実装
- **非同期処理**: I/Oバウンドな処理（API呼び出し、DB操作）は非同期で実装
- **設定の外部化**: ハードコードを避け、環境変数や設定ファイルを使用
- **Docker最適化**: マルチステージビルドやレイヤーキャッシュを活用した効率的なイメージ構築
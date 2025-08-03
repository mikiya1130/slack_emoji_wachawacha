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
      
      async def handle_message(self, message: dict) -> None:
          """メッセージを受信し、絵文字リアクションを付与"""
          pass
      
      async def add_reactions(self, channel: str, timestamp: str, emojis: List[str]) -> None:
          """指定されたメッセージに絵文字リアクションを追加"""
          pass
      
      # スラッシュコマンドハンドラー
      async def handle_emoji_command(self, ack, command: dict, client) -> None:
          """絵文字管理スラッシュコマンドのルーティング"""
          pass
      
      async def cmd_add_emoji(self, ack, command: dict, client) -> None:
          """新しい絵文字を追加（モーダル表示）"""
          pass
      
      async def cmd_list_emojis(self, ack, command: dict, client) -> None:
          """絵文字一覧を表示"""
          pass
      
      async def cmd_search_emojis(self, ack, command: dict, client) -> None:
          """絵文字を検索"""
          pass
      
      async def cmd_delete_emoji(self, ack, command: dict, client) -> None:
          """絵文字を削除"""
          pass
      
      async def cmd_update_emoji(self, ack, command: dict, client) -> None:
          """絵文字情報を更新（モーダル表示）"""
          pass
      
      async def cmd_vectorize_emojis(self, ack, command: dict, client) -> None:
          """全絵文字のベクトル化を実行"""
          pass
      
      async def cmd_emoji_stats(self, ack, command: dict, client) -> None:
          """絵文字の統計情報を表示"""
          pass
      
      # モーダル/インタラクションハンドラー
      async def handle_add_emoji_modal_submission(self, ack, body, client) -> None:
          """絵文字追加モーダルの送信処理"""
          pass
      
      async def handle_update_emoji_modal_submission(self, ack, body, client) -> None:
          """絵文字更新モーダルの送信処理"""
          pass
      
      # ボタンアクションハンドラー
      async def handle_vectorize_confirm(self, ack, body, client) -> None:
          """ベクトル化実行確認ボタンの処理"""
          pass
      
      async def handle_vectorize_cancel(self, ack, body, client) -> None:
          """ベクトル化キャンセルボタンの処理"""
          pass
  ```
- **内部実装方針**: 
  - Slack Bolt FrameworkのSocket Modeを使用
  - メッセージフィルタリング（Bot自身の投稿除外）を実装
  - 非同期処理でリアクション送信のパフォーマンスを確保
  - スラッシュコマンドのルーティングとエラーハンドリング
  - モーダルビューの構築とインタラクション処理

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
      
      # CRUD操作
      async def add_emoji(self, emoji_data: EmojiData) -> EmojiData:
          """新しい絵文字を追加"""
          pass
      
      async def update_emoji(self, emoji_id: int, emoji_data: EmojiData) -> EmojiData:
          """既存の絵文字を更新"""
          pass
      
      async def delete_emoji(self, emoji_code: str) -> bool:
          """絵文字を削除"""
          pass
      
      async def get_emoji_by_code(self, emoji_code: str) -> Optional[EmojiData]:
          """コードで絵文字を取得"""
          pass
      
      async def list_emojis(self, category: Optional[str] = None, 
                           emotion_tone: Optional[str] = None,
                           offset: int = 0, 
                           limit: int = 20) -> List[EmojiData]:
          """絵文字一覧を取得（フィルタリング対応）"""
          pass
      
      async def search_emojis(self, keyword: str) -> List[EmojiData]:
          """キーワードで絵文字を検索"""
          pass
      
      async def vectorize_all_emojis(self, skip_existing: bool = True) -> Dict[str, Any]:
          """全絵文字のベクトル化を実行"""
          pass
      
      async def get_emoji_stats(self) -> Dict[str, Any]:
          """絵文字の統計情報を取得"""
          pass
  ```
- **内部実装方針**: 
  - pgvectorのコサイン類似度検索を使用
  - 絵文字メタデータ（コード、説明文、カテゴリ、感情トーン、使用シーン、優先度）を管理
  - バリデーション処理（重複チェック、形式チェック）
  - 一括処理での効率的なベクトル化

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

#### メッセージリアクションフロー
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

#### スラッシュコマンドフロー
```
スラッシュコマンド受信
/emoji <subcommand> [args]
        │
        ▼
  [SlackHandler]
   コマンドルーティング
        │
        ├─── /emoji add ──────► モーダル表示
        │                             │
        ├─── /emoji list ─────► 一覧表示処理
        │                             │
        ├─── /emoji search ───► 検索処理
        │                             │
        ├─── /emoji delete ───► 削除確認・処理
        │                             │
        ├─── /emoji update ───► モーダル表示
        │                             │
        ├─── /emoji vectorize ► 非同期処理開始
        │                             │
        └─── /emoji stats ────► 統計情報生成
                                      │
                                      ▼
                              [EmojiService]
                               CRUD/分析処理
                                      │
                                      ▼
                              エフェメラルメッセージ
                              またはモーダル応答
```

### 3.2 データ変換

#### メッセージイベント
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

#### スラッシュコマンドイベント
- **入力データ形式**: Slack スラッシュコマンドペイロード（JSON）
  ```json
  {
    "token": "verification_token",
    "team_id": "T123456789",
    "team_domain": "workspace",
    "channel_id": "C123456789",
    "channel_name": "general",
    "user_id": "U123456789",
    "user_name": "username",
    "command": "/emoji",
    "text": "add :custom_emoji: これはカスタム絵文字です",
    "response_url": "https://hooks.slack.com/commands/1234/5678",
    "trigger_id": "13345224609.738474920.8088930838d88f008e0"
  }
  ```

- **モーダルビューの例**: 絵文字追加フォーム
  ```json
  {
    "type": "modal",
    "callback_id": "add_emoji_modal",
    "title": {
      "type": "plain_text",
      "text": "絵文字を追加"
    },
    "blocks": [
      {
        "type": "input",
        "block_id": "emoji_code",
        "label": {
          "type": "plain_text",
          "text": "絵文字コード"
        },
        "element": {
          "type": "plain_text_input",
          "action_id": "emoji_code_input",
          "placeholder": {
            "type": "plain_text",
            "text": ":custom_emoji:"
          }
        }
      },
      {
        "type": "input",
        "block_id": "description",
        "label": {
          "type": "plain_text",
          "text": "説明文"
        },
        "element": {
          "type": "plain_text_input",
          "action_id": "description_input",
          "multiline": true
        }
      },
      {
        "type": "section",
        "block_id": "metadata",
        "text": {
          "type": "mrkdwn",
          "text": "メタデータ"
        },
        "accessory": {
          "type": "static_select",
          "action_id": "category_select",
          "placeholder": {
            "type": "plain_text",
            "text": "カテゴリを選択"
          },
          "options": [
            {
              "text": {"type": "plain_text", "text": "感情"},
              "value": "emotion"
            },
            {
              "text": {"type": "plain_text", "text": "行動"},
              "value": "action"
            },
            {
              "text": {"type": "plain_text", "text": "物"},
              "value": "object"
            }
          ]
        }
      }
    ]
  }
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
    created_by VARCHAR(50),             -- 作成者のSlackユーザーID
    updated_by VARCHAR(50),             -- 更新者のSlackユーザーID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ベクトル検索用インデックス
CREATE INDEX ON emojis USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- カテゴリ検索用インデックス
CREATE INDEX idx_emojis_category ON emojis(category);
-- 感情トーン検索用インデックス
CREATE INDEX idx_emojis_emotion_tone ON emojis(emotion_tone);
```

#### admin_users テーブル（権限管理）
```sql
CREATE TABLE admin_users (
    id SERIAL PRIMARY KEY,
    slack_user_id VARCHAR(50) NOT NULL UNIQUE,  -- SlackユーザーID
    slack_user_name VARCHAR(100),                -- Slackユーザー名（キャッシュ用）
    permission_level VARCHAR(20) DEFAULT 'editor', -- admin, editor, viewer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 権限レベル定義:
-- admin: 全権限（ユーザー管理、削除、更新など）
-- editor: 絵文字の追加・更新が可能
-- viewer: 閲覧のみ
```

#### emoji_usage_logs テーブル（使用状況追跡）
```sql
CREATE TABLE emoji_usage_logs (
    id SERIAL PRIMARY KEY,
    emoji_code VARCHAR(100) NOT NULL,
    channel_id VARCHAR(50),
    user_id VARCHAR(50),
    message_ts VARCHAR(50),
    usage_type VARCHAR(20), -- reaction, command
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 統計用インデックス
CREATE INDEX idx_usage_logs_emoji ON emoji_usage_logs(emoji_code);
CREATE INDEX idx_usage_logs_created ON emoji_usage_logs(created_at);
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
  - スラッシュコマンド: `/emoji` コマンドの受信
  - インタラクティブコンポーネント: モーダル送信、ボタンクリック

- **Slack API (送信)**
  - `reactions.add`: 絵文字リアクション追加
  - `views.open`: モーダルビューの表示
  - `views.update`: モーダルビューの更新
  - `chat.postMessage`: メッセージ送信
  - `chat.postEphemeral`: エフェメラルメッセージ送信
  - `chat.update`: メッセージ更新

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

## 12. スラッシュコマンド詳細設計

### 12.1 コマンド構文

```
/emoji <subcommand> [arguments]
```

#### サブコマンド一覧

| サブコマンド | 構文 | 説明 | 権限 |
|---|---|---|---|
| add | `/emoji add` | モーダルを表示して絵文字を追加 | editor以上 |
| list | `/emoji list [category] [emotion]` | 絵文字一覧を表示 | 全ユーザー |
| search | `/emoji search <keyword>` | キーワードで絵文字を検索 | 全ユーザー |
| delete | `/emoji delete <emoji_code>` | 絵文字を削除 | admin |
| update | `/emoji update <emoji_code>` | モーダルを表示して絵文字を更新 | editor以上 |
| vectorize | `/emoji vectorize [--force]` | 全絵文字のベクトル化（確認あり） | admin |
| stats | `/emoji stats [category]` | 統計情報を表示 | 全ユーザー |

### 12.2 応答パターン

#### 即座の応答（エフェメラルメッセージ）
```python
# 軽量な処理の場合
await ack()
await respond({
    "text": "絵文字一覧を取得しています...",
    "response_type": "ephemeral"
})
```

#### 非同期処理パターン
```python
# 重い処理の場合（vectorize等）
await ack({
    "text": "ベクトル化処理を開始しました。完了後にお知らせします。",
    "response_type": "ephemeral"
})

# バックグラウンドタスクで処理
asyncio.create_task(vectorize_all_emojis_task(command))
```

#### 確認付き処理パターン（vectorize）
```python
# vectorizeコマンドの場合、まず確認メッセージを表示
await ack()
await client.chat_postEphemeral(
    channel=command["channel_id"],
    user=command["user_id"],
    blocks=[
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "全絵文字のベクトル化を実行しますか？\n"
                       f"• 対象絵文字数: {emoji_count}\n"
                       f"• 推定処理時間: 約{estimated_time}分\n"
                       f"• {"*強制実行モード*" if force else "既存のベクトルはスキップ"}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "実行"},
                    "style": "primary",
                    "action_id": "vectorize_confirm",
                    "value": json.dumps({"force": force})
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "キャンセル"},
                    "action_id": "vectorize_cancel"
                }
            ]
        }
    ]
)
```

### 12.3 モーダルビュー設計

#### 絵文字追加モーダル
- 必須フィールド：絵文字コード、説明文
- オプションフィールド：カテゴリ、感情トーン、使用シーン、優先度
- バリデーション：絵文字形式チェック、重複チェック

#### 絵文字更新モーダル
- 既存データのプリフィル
- 変更履歴の記録（updated_by）

## 13. 権限管理設計

### 13.1 権限レベル

| レベル | 権限 | 対象機能 |
|---|---|---|
| admin | 全権限 | 全機能（ユーザー管理含む） |
| editor | 編集権限 | 追加、更新、ベクトル化 |
| viewer | 閲覧権限 | 一覧、検索、統計のみ |

### 13.2 権限チェック実装

```python
async def check_permission(user_id: str, required_level: str) -> bool:
    """ユーザーの権限をチェック"""
    user = await get_admin_user(user_id)
    if not user:
        return required_level == "viewer"  # デフォルトはviewer権限
    
    permission_hierarchy = {
        "viewer": 0,
        "editor": 1,
        "admin": 2
    }
    
    user_level = permission_hierarchy.get(user.permission_level, 0)
    required = permission_hierarchy.get(required_level, 0)
    
    return user_level >= required
```

## 14. 非同期処理設計

### 14.1 バックグラウンドタスク

#### ベクトル化タスク
```python
async def vectorize_all_emojis_task(command: dict, force: bool = False):
    """全絵文字のベクトル化をバックグラウンドで実行"""
    try:
        # 進捗通知の開始
        await send_progress_message(command["channel_id"], 
                                  command["user_id"], 
                                  "ベクトル化処理を開始しました...")
        
        # 処理実行
        result = await emoji_service.vectorize_all_emojis(skip_existing=not force)
        
        # 完了通知
        await send_completion_message(command["channel_id"], 
                                    command["user_id"], 
                                    f"ベクトル化が完了しました: {result}")
    except Exception as e:
        # エラー通知
        await send_error_message(command["channel_id"], 
                               command["user_id"], 
                               f"エラーが発生しました: {str(e)}")
```

#### 確認ボタンハンドラー
```python
async def handle_vectorize_confirm(self, ack, body, client):
    """ベクトル化実行確認ボタンクリック時の処理"""
    await ack()
    
    # ボタンのvalueからパラメータを取得
    action_value = json.loads(body["actions"][0]["value"])
    force = action_value.get("force", False)
    
    # 元のメッセージを更新（処理開始を通知）
    await client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="ベクトル化処理を開始しました。完了まで暫くお待ちください。"
    )
    
    # バックグラウンドタスクで実行
    command_info = {
        "channel_id": body["channel"]["id"],
        "user_id": body["user"]["id"]
    }
    asyncio.create_task(vectorize_all_emojis_task(command_info, force))

async def handle_vectorize_cancel(self, ack, body, client):
    """ベクトル化キャンセルボタンクリック時の処理"""
    await ack()
    
    # 元のメッセージを更新（キャンセルを通知）
    await client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="ベクトル化処理をキャンセルしました。"
    )
```

### 14.2 進捗通知

- スレッドでの進捗報告
- 処理中のスピナー表示
- 完了時の結果サマリー

## 15. 実装上の注意事項

- **コードのシンプルさ優先**: 過度な抽象化を避け、理解しやすい実装を心がける
- **最小限の実装**: 必要最小限の機能から開始し、段階的に拡張
- **エラーハンドリング**: 外部API呼び出し時の適切な例外処理
- **ログ出力**: 現時点では簡素化、将来的にエラー追跡用で追加
- **テスト**: 主要な処理フローに対する単体テスト・統合テストの実装
- **非同期処理**: I/Oバウンドな処理（API呼び出し、DB操作）は非同期で実装
- **設定の外部化**: ハードコードを避け、環境変数や設定ファイルを使用
- **Docker最適化**: マルチステージビルドやレイヤーキャッシュを活用した効率的なイメージ構築
- **スラッシュコマンド**: 3秒以内の応答、重い処理は非同期化
- **権限管理**: 最小権限の原則、デフォルトはviewer権限
- **破壊的操作の確認**: vectorizeなどの重い処理や削除操作では必ず確認ステップを挟む
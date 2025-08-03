# Slack Emoji Reaction Bot Project Overview

## プロジェクトの目的
RAG（Retrieval-Augmented Generation）とベクトル類似度検索を用いて、Slackメッセージに文脈に適した絵文字リアクションを自動的に追加するBotです。さらに、スラッシュコマンドによる絵文字管理機能を実装予定です。

## 技術スタック
- **言語**: Python 3.12+
- **フレームワーク**: slack-bolt-python (Socket Mode)
- **データベース**: PostgreSQL 16+ with pgvector extension
- **AI**: OpenAI text-embedding-3-small model
- **コンテナ**: Docker & Docker Compose

## 主要コンポーネント
1. **SlackHandler**: Slackイベント処理（メッセージ、スラッシュコマンド）
2. **OpenAIService**: テキストのベクトル化
3. **EmojiService**: 絵文字データ管理と類似度検索
4. **DatabaseService**: PostgreSQL/pgvector操作

## データフロー
1. Slackメッセージ/コマンド受信（Socket Mode）
2. テキストをOpenAI APIでベクトル化
3. pgvectorで類似絵文字を検索
4. 上位3つの絵文字をリアクション/返信

## 開発アプローチ
- TDD（テスト駆動開発）厳守
- 80%以上のテストカバレッジ維持
- コードのシンプルさ優先
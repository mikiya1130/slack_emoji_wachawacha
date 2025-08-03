"""
SlackHandler - Slack integration service

TDD REFACTOR Phase: 高品質で最適化されたSlack連携機能

Features:
- Slack Bolt Framework (Socket Mode) integration
- Advanced emoji reaction system with retry logic
- Concurrent processing for performance
- Exponential backoff and rate limit monitoring
- Comprehensive error handling and logging
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError
from app.utils.logging import get_logger
from app.config import Config

logger = get_logger("slack_handler")

# Constants for retry and rate limiting
DEFAULT_MAX_RETRIES = 2
DEFAULT_BASE_DELAY = 1.0
MAX_BACKOFF_DELAY = 30.0
CONCURRENT_REACTION_LIMIT = 10  # 同時処理可能な絵文字数


class SlackHandler:
    """
    Slack連携を担当するハンドラー

    責務:
    - Slack Bolt Framework（Socket Mode）の管理
    - メッセージ受信・処理
    - Bot自身のメッセージフィルタリング
    - 絵文字リアクション送信
    """

    def __init__(self, openai_service, emoji_service):
        """
        SlackHandlerの初期化

        Args:
            openai_service: OpenAI APIサービス
            emoji_service: 絵文字管理サービス
        """
        self.openai_service = openai_service
        self.emoji_service = emoji_service

        # 設定を取得
        config = Config()

        # Slack Bolt App（実際の実装）
        self.app = AsyncApp(token=config.slack.bot_token)

        # Socket Mode Handler（実際の実装）
        self.socket_mode_handler = AsyncSocketModeHandler(
            self.app, config.slack.app_token
        )

        # メッセージハンドラーを登録
        self._register_handlers()

        # 高度な機能用の設定（定数を使用）
        self.max_retries = DEFAULT_MAX_RETRIES
        self.base_delay = DEFAULT_BASE_DELAY
        self.max_backoff_delay = MAX_BACKOFF_DELAY
        self.concurrent_limit = CONCURRENT_REACTION_LIMIT

        # レート制限監視とメトリクス
        self.rate_limit_info = {}
        self.reaction_metrics = {
            "total_reactions": 0,
            "successful_reactions": 0,
            "failed_reactions": 0,
            "retries_performed": 0,
        }

        # スラッシュコマンドハンドラー
        self.slash_command_handler = None

        logger.info(
            f"SlackHandler initialized with advanced features: "
            f"max_retries={self.max_retries}, base_delay={self.base_delay}s, "
            f"concurrent_limit={self.concurrent_limit}"
        )

    def _register_handlers(self):
        """Slackイベントハンドラーを登録"""

        # メッセージイベントのハンドラーを登録
        @self.app.event("message")
        async def handle_message_events(event, ack):
            """Slackメッセージイベントを処理"""
            try:
                # イベントの確認応答を送信
                await ack()
                # メッセージ処理
                await self.handle_message(event)
            except Exception as e:
                logger.error(f"Error in message event handler: {e}")

        # /emoji スラッシュコマンドのハンドラーを登録
        @self.app.command("/emoji")
        async def handle_emoji_command(ack, command, respond):
            """Emoji関連のスラッシュコマンドを処理"""
            try:
                await ack()
                await self._handle_emoji_slash_command(command, respond)
            except Exception as e:
                logger.error(f"Error in emoji slash command handler: {e}")
                await respond(
                    {
                        "text": "エラーが発生しました。しばらく待ってから再試行してください。"
                    }
                )

        # vectorize_confirmアクションハンドラーを登録
        @self.app.action("vectorize_confirm")
        async def handle_vectorize_confirm(ack, body, action):
            """ベクトル化確認アクションを処理"""
            try:
                await ack()
                if self.slash_command_handler:
                    await self.slash_command_handler.handle_action(body)
            except Exception as e:
                logger.error(f"Error in vectorize_confirm action handler: {e}")

        # vectorize_cancelアクションハンドラーを登録
        @self.app.action("vectorize_cancel")
        async def handle_vectorize_cancel(ack, body, action):
            """ベクトル化キャンセルアクションを処理"""
            try:
                await ack()
                if self.slash_command_handler:
                    await self.slash_command_handler.handle_action(body)
            except Exception as e:
                logger.error(f"Error in vectorize_cancel action handler: {e}")

        # emoji_add_modalのview_submissionハンドラーを登録
        @self.app.view("emoji_add_modal")
        async def handle_emoji_add_submission(ack, body, view):
            """絵文字追加モーダルの送信を処理"""
            try:
                await ack()
                if self.slash_command_handler:
                    result = await self.slash_command_handler.handle_emoji_add_submission(body)
                    # 結果メッセージがある場合は送信
                    if result and "text" in result:
                        user_id = body["user"]["id"]
                        await self.app.client.chat_postMessage(
                            channel=user_id,
                            text=result["text"]
                        )
            except Exception as e:
                logger.error(f"Error in emoji_add_modal submission handler: {e}")
                await ack(response_action="errors", errors={"error": str(e)})

    async def start(self):
        """Start the Slack handler and Socket Mode connection."""
        logger.info("Starting Slack handler...")
        try:
            # Socket Mode接続を非同期で開始
            await self.socket_mode_handler.start_async()
            logger.info("Slack handler started successfully")
        except Exception as e:
            logger.error(f"Failed to start Slack handler: {e}")
            raise

    async def stop(self):
        """Stop the Slack handler and close connections."""
        logger.info("Stopping Slack handler...")
        try:
            # Socket Mode接続を閉じる
            if hasattr(self, "socket_mode_handler"):
                await self.socket_mode_handler.close_async()

            logger.info("Slack handler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping Slack handler: {e}")
            # エラーがあっても停止プロセスは継続

    async def handle_message(self, message: Dict[str, Any]) -> None:
        """
        Slackメッセージを受信し、絵文字リアクションを付与

        Args:
            message: Slackメッセージデータ
        """
        try:
            # メッセージフィルタリング
            if not self._should_process_message(message):
                logger.debug(f"Message filtered: {message}")
                return

            # 共通処理を使用してリアクションを追加
            result = await self._process_message_with_reactions(
                text=message.get("text", "").strip(),
                channel=message["channel"],
                timestamp=message["ts"],
            )

            if result and result.get("status") == "success":
                logger.info(
                    f"Added reactions {result['emojis_added']} to message {message['ts']}"
                )

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            # エラーが発生しても例外を上げない（graceful handling）

    def _should_process_message(self, message: Dict[str, Any]) -> bool:
        """
        メッセージを処理すべきかどうかを判定

        Args:
            message: Slackメッセージデータ

        Returns:
            bool: 処理すべきならTrue
        """
        # メッセージタイプの確認
        if message.get("type") != "message":
            return False

        # サブタイプのあるメッセージ（システムメッセージなど）をフィルタ
        if message.get("subtype"):
            return False

        # Bot自身のメッセージをフィルタ
        if message.get("bot_id"):
            return False

        # Slack botのメッセージをフィルタ
        user_id = message.get("user")
        if user_id and (user_id == "USLACKBOT" or user_id.startswith("B")):
            return False

        return True

    async def add_reactions(
        self, channel: str, timestamp: str, emojis: List[str]
    ) -> None:
        """
        指定されたメッセージに絵文字リアクションを追加（高品質実装）

        Features:
        - 並行処理による高速化（制限付き）
        - リトライ処理と指数バックオフ
        - レート制限監視とメトリクス追跡
        - 包括的なエラーハンドリング

        Args:
            channel: チャンネルID
            timestamp: メッセージのタイムスタンプ
            emojis: 追加する絵文字のリスト（例: [":smile:", ":thumbsup:"]）

        Raises:
            ValueError: 無効な引数が渡された場合
        """
        # 入力検証
        if not emojis:
            logger.debug("No emojis provided, skipping reaction addition")
            return

        if not channel or not timestamp:
            raise ValueError("Channel and timestamp must be provided")

        # 大量の絵文字処理の制限
        if len(emojis) > self.concurrent_limit:
            logger.warning(
                f"Too many emojis ({len(emojis)}), limiting to {self.concurrent_limit}"
            )
            emojis = emojis[: self.concurrent_limit]

        # メトリクス更新
        self.reaction_metrics["total_reactions"] += len(emojis)

        # 並行処理でリアクションを追加
        tasks = []
        for emoji in emojis:
            emoji_name = self._sanitize_emoji_name(emoji)
            if emoji_name:  # 有効な絵文字名のみ処理
                task = self._add_single_reaction_with_retry(
                    channel, timestamp, emoji_name
                )
                tasks.append(task)

        if not tasks:
            logger.warning("No valid emojis to process")
            return

        # すべてのリアクションを並行実行
        start_time = time.time()
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 結果の分析
            successful_count = sum(
                1 for result in results if not isinstance(result, Exception)
            )
            failed_count = len(results) - successful_count

            # メトリクス更新
            self.reaction_metrics["successful_reactions"] += successful_count
            self.reaction_metrics["failed_reactions"] += failed_count

            elapsed_time = time.time() - start_time

            logger.info(
                f"Reaction processing complete: {successful_count}/{len(results)} successful "
                f"in {elapsed_time:.2f}s for {channel}:{timestamp}"
            )

            if failed_count > 0:
                logger.warning(f"{failed_count} reactions failed")

        except Exception as e:
            logger.error(f"Critical error in concurrent reaction processing: {e}")
            self.reaction_metrics["failed_reactions"] += len(tasks)

    def _sanitize_emoji_name(self, emoji: str) -> Optional[str]:
        """
        絵文字名をサニタイズして有効性をチェック

        Args:
            emoji: 絵文字文字列

        Returns:
            Optional[str]: サニタイズされた絵文字名、無効な場合はNone
        """
        if not emoji or not isinstance(emoji, str):
            return None

        # コロンを除去
        emoji_name = emoji.strip().strip(":")

        # 空文字列や無効な文字をチェック
        if not emoji_name or len(emoji_name) > 100:  # Slack制限
            logger.debug(f"Invalid emoji name: {emoji}")
            return None

        return emoji_name

    async def _add_single_reaction_with_retry(
        self, channel: str, timestamp: str, emoji_name: str
    ) -> None:
        """
        単一の絵文字リアクションをリトライ処理付きで追加

        Args:
            channel: チャンネルID
            timestamp: メッセージのタイムスタンプ
            emoji_name: 絵文字名（:なし）

        Raises:
            Exception: 最大リトライ回数に達した場合
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):  # 初回 + リトライ
            try:
                # Slack APIを呼び出し（非同期クライアント使用）
                response = await self.app.client.reactions_add(
                    channel=channel, timestamp=timestamp, name=emoji_name
                )

                # レート制限情報を記録
                self._update_rate_limit_info(response)

                # 成功ログ（リトライした場合のみ詳細表示）
                if attempt > 0:
                    logger.info(
                        f"Successfully added reaction {emoji_name} after {attempt} retries"
                    )
                    self.reaction_metrics["retries_performed"] += attempt
                else:
                    logger.debug(
                        f"Added reaction {emoji_name} to {channel}:{timestamp}"
                    )

                return  # 成功時は即座にリターン

            except SlackApiError as e:
                last_error = e
                error_msg = e.response.get("error", str(e))
            except Exception as e:
                # SlackApiError以外の例外をキャッチ
                last_error = e
                error_msg = str(e)

                # 既にリアクション済みの場合は成功として扱う
                if "already_reacted" in error_msg:
                    logger.debug(f"Reaction {emoji_name} already exists on message")
                    return  # 成功として扱う

                # リトライ可能なエラーかチェック
                if self._is_retryable_error(error_msg) and attempt < self.max_retries:
                    delay = self._calculate_exponential_backoff(attempt)
                    logger.warning(
                        f"Retryable error for {emoji_name} (attempt {attempt + 1}): "
                        f"{error_msg}. Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    # 最終試行 or リトライ不可能なエラー
                    if attempt == self.max_retries:
                        logger.error(
                            f"Max retries ({self.max_retries}) exceeded for "
                            f"{emoji_name}: {error_msg}"
                        )
                    else:
                        logger.error(
                            f"Non-retryable error for {emoji_name}: {error_msg}"
                        )

                    # 最終的なエラーを再発生
                    if last_error:
                        raise last_error
                    else:
                        raise Exception(f"Failed to add reaction {emoji_name}")

    def _is_retryable_error(self, error_msg: str) -> bool:
        """
        リトライ可能なエラーかどうかを判定

        Args:
            error_msg: エラーメッセージ

        Returns:
            bool: リトライ可能ならTrue
        """
        retryable_errors = [
            "rate_limited",
            "timeout",
            "server_error",
            "connection_error",
            "service_unavailable",
        ]

        error_lower = error_msg.lower()
        return any(
            retryable_error in error_lower for retryable_error in retryable_errors
        )

    def _calculate_exponential_backoff(self, attempt: int) -> float:
        """
        指数バックオフによる遅延時間を計算

        Formula: base_delay * (2 ^ attempt)
        最大遅延時間で制限される

        Args:
            attempt: 試行回数（0から開始）

        Returns:
            float: 遅延時間（秒）
        """
        # 指数バックオフ: base_delay * (2 ^ attempt)
        delay = self.base_delay * (2**attempt)

        # 最大遅延時間に制限
        return min(delay, self.max_backoff_delay)

    def _update_rate_limit_info(self, response) -> None:
        """
        レート制限情報を更新

        Args:
            response: Slack APIのレスポンス
        """
        try:
            # Slack SDKのレスポンスからヘッダー情報を取得
            if hasattr(response, "headers"):
                headers = response.headers
                self.rate_limit_info = {
                    "remaining": headers.get("X-Rate-Limit-Remaining"),
                    "reset": headers.get("X-Rate-Limit-Reset"),
                    "retry_after": headers.get("Retry-After"),
                    "last_updated": time.time(),
                }
                logger.debug(f"Rate limit info updated: {self.rate_limit_info}")
        except Exception as e:
            logger.debug(f"Could not update rate limit info: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """
        パフォーマンスメトリクスを取得

        Returns:
            Dict[str, Any]: メトリクス情報
        """
        total = self.reaction_metrics["total_reactions"]
        successful = self.reaction_metrics["successful_reactions"]

        return {
            **self.reaction_metrics,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "rate_limit_info": self.rate_limit_info.copy(),
            "configuration": {
                "max_retries": self.max_retries,
                "base_delay": self.base_delay,
                "max_backoff_delay": self.max_backoff_delay,
                "concurrent_limit": self.concurrent_limit,
            },
        }

    def reset_metrics(self) -> None:
        """メトリクスをリセット"""
        self.reaction_metrics = {
            "total_reactions": 0,
            "successful_reactions": 0,
            "failed_reactions": 0,
            "retries_performed": 0,
        }
        logger.info("Reaction metrics reset")

    # RAG Integration Methods

    async def _process_message_with_reactions(
        self,
        text: str,
        channel: str,
        timestamp: str,
        fallback_emojis: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        メッセージ処理とリアクション追加の共通ロジック

        Args:
            text: メッセージテキスト
            channel: チャンネルID
            timestamp: メッセージタイムスタンプ
            fallback_emojis: フォールバック絵文字

        Returns:
            処理結果辞書
        """
        # 空メッセージチェック
        if not text:
            logger.debug("Skipping empty message")
            return None

        # チャンネル・タイムスタンプの検証
        if not channel or not timestamp:
            logger.warning("Missing channel or timestamp in message")
            return None

        try:
            # OpenAI APIでメッセージをベクトル化
            logger.info(f"Processing message: {text[:50]}...")
            embedding = await self.openai_service.get_embedding(text)

            # EmojiServiceで類似絵文字を検索
            similar_emojis = await self.emoji_service.find_similar_emojis(
                embedding, limit=Config.DEFAULT_REACTION_COUNT
            )

            if similar_emojis:
                # 絵文字コードを正規化（コロンを除去）
                sanitized_names = [
                    self._sanitize_emoji_name(emoji.code) for emoji in similar_emojis
                ]
                emoji_names = [name for name in sanitized_names if name is not None]

                if emoji_names:
                    # レート制限チェック
                    if hasattr(self, "rate_limit_max"):
                        await self._check_rate_limit()

                    # リアクション追加
                    await self.add_reactions(channel, timestamp, emoji_names)

                    return {
                        "status": "success",
                        "emojis_added": emoji_names,
                        "message": text[:50] + "..." if len(text) > 50 else text,
                    }

            logger.info(f"No emojis found for message: {text[:50]}...")
            return {"status": "no_emojis", "message": text[:50]}

        except Exception as e:
            logger.error(f"Error processing message for reactions: {e}")

            # フォールバック絵文字使用
            if fallback_emojis:
                try:
                    await self.add_reactions(channel, timestamp, fallback_emojis)
                    return {"status": "fallback", "emojis_added": fallback_emojis}
                except Exception as fallback_error:
                    logger.error(f"Fallback emoji addition failed: {fallback_error}")

            return {"status": "error", "error": str(e)}

    def set_emoji_service(self, emoji_service) -> None:
        """Set the emoji service for RAG integration"""
        self.emoji_service = emoji_service
        logger.info("EmojiService connected to SlackHandler")

    def set_slash_command_handler(self, slash_command_handler) -> None:
        """Set the slash command handler for /emoji commands"""
        self.slash_command_handler = slash_command_handler
        logger.info("SlashCommandHandler connected to SlackHandler")

    async def process_message_for_reactions(
        self, message_event: Dict[str, Any], fallback_emojis: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process a Slack message and add emoji reactions using RAG

        Args:
            message_event: Slack message event
            fallback_emojis: Optional fallback emojis if RAG fails

        Returns:
            Processing result or None
        """
        # 共通処理を使用
        channel = message_event.get("channel")
        timestamp = message_event.get("ts")

        # 型安全性のためのチェック
        if not isinstance(channel, str) or not isinstance(timestamp, str):
            logger.warning("Invalid channel or timestamp type in message event")
            return {"status": "error", "error": "Invalid message format"}

        return await self._process_message_with_reactions(
            text=message_event.get("text", "").strip(),
            channel=channel,
            timestamp=timestamp,
            fallback_emojis=fallback_emojis,
        )

    def set_emoji_filters(
        self, category: Optional[str] = None, emotion_tone: Optional[str] = None
    ) -> None:
        """Set emoji filtering preferences"""
        self.emoji_filter_category = category
        self.emoji_filter_emotion = emotion_tone
        logger.info(f"Emoji filters set: category={category}, emotion={emotion_tone}")

    def set_rate_limit(self, max_reactions_per_minute: int) -> None:
        """Set rate limiting for reactions"""
        self.rate_limit_max = max_reactions_per_minute
        self.rate_limit_window: List[float] = []  # Timestamps of recent reactions
        logger.info(f"Rate limit set to {max_reactions_per_minute} reactions/minute")

    async def check_rag_health(self) -> Dict[str, Any]:
        """Check health status of RAG integration components"""
        health_status = {
            "slack_connected": bool(self.app and self.app.client),
            "openai_available": False,
            "database_connected": False,
            "emoji_count": 0,
        }

        # Check emoji service
        if hasattr(self, "emoji_service") and self.emoji_service:
            try:
                # Check OpenAI service
                if hasattr(self.emoji_service, "openai_service"):
                    health_status["openai_available"] = (
                        self.emoji_service.openai_service is not None
                    )

                # Check database by counting emojis
                emoji_count = await self.emoji_service.count_emojis()
                health_status["database_connected"] = True
                health_status["emoji_count"] = emoji_count

            except Exception as e:
                logger.error(f"Health check failed: {e}")

        return health_status

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting"""
        if not hasattr(self, "rate_limit_max"):
            return

        now = time.time()
        # Remove old timestamps outside the window
        self.rate_limit_window = [ts for ts in self.rate_limit_window if now - ts < 60]

        # Check if we're at the limit
        if len(self.rate_limit_window) >= self.rate_limit_max:
            # Wait until the oldest timestamp expires
            wait_time = 60 - (now - self.rate_limit_window[0]) + 0.1
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                # Re-clean the window after waiting
                now = time.time()
                self.rate_limit_window = [
                    ts for ts in self.rate_limit_window if now - ts < 60
                ]

        # Add current timestamp
        self.rate_limit_window.append(now)

    # Slash command methods

    async def _handle_emoji_slash_command(self, command, respond) -> None:
        """
        /emoji スラッシュコマンドの処理

        Args:
            command: Slackコマンド情報
            respond: レスポンス関数
        """
        # SlashCommandHandlerが設定されている場合は委譲
        if self.slash_command_handler:
            try:
                # SlashCommandHandlerに処理を委譲
                response = await self.slash_command_handler.handle_emoji_command(
                    command
                )
                await respond(response)
            except Exception as e:
                logger.error(f"Error in slash command handler: {e}")
                await respond(
                    {
                        "response_type": "ephemeral",
                        "text": "コマンド処理中にエラーが発生しました。しばらく待ってから再試行してください。",
                    }
                )
        else:
            # フォールバック: 基本機能のみ
            text = command.get("text", "").strip()

            if not text or text == "help":
                await self._show_emoji_help(respond)
            elif text == "status":
                await self._show_emoji_status(respond)
            elif text == "metrics":
                await self._show_emoji_metrics(respond)
            else:
                await respond(
                    {
                        "text": f"不明なコマンド: `{text}`\n`/emoji help` でヘルプを表示します。"
                    }
                )

    async def _show_emoji_help(self, respond) -> None:
        """絵文字ボットのヘルプを表示"""
        help_text = """
*🤖 Emoji Bot ヘルプ*

このボットは、メッセージの内容に基づいて適切な絵文字リアクションを自動で追加します。

*利用可能なコマンド:*
• `/emoji help` - このヘルプを表示
• `/emoji status` - ボットの状態を確認
• `/emoji metrics` - 絵文字追加の統計を表示

*機能:*
• 🎯 AIによる文脈に沿った絵文字の自動選択
• 🚀 高速な並行処理による絵文字追加
• 📊 使用統計とパフォーマンス監視
• 🛡️ エラー処理とリトライ機能

何か問題がありましたら、管理者にお問い合わせください。
        """
        await respond({"text": help_text.strip()})

    async def _show_emoji_status(self, respond) -> None:
        """ボットの状態を表示"""
        try:
            health = await self.check_rag_health()
            status_text = f"""
*🤖 Emoji Bot ステータス*

• Slack接続: {'✅ 正常' if health['slack_connected'] else '❌ 異常'}
• OpenAI API: {'✅ 利用可能' if health['openai_available'] else '❌ 異常'}
• データベース: {'✅ 接続済み' if health['database_connected'] else '❌ 接続失敗'}
• 絵文字データ: {health['emoji_count']} 件

*設定:*
• 最大リトライ回数: {self.max_retries}
• 並行処理制限: {self.concurrent_limit}
• ベース遅延: {self.base_delay}秒
            """
            await respond({"text": status_text.strip()})
        except Exception as e:
            logger.error(f"Error getting emoji status: {e}")
            await respond({"text": "ステータス取得中にエラーが発生しました。"})

    async def _show_emoji_metrics(self, respond) -> None:
        """絵文字追加の統計を表示"""
        try:
            metrics = self.get_metrics()
            metrics_text = f"""
*📊 Emoji Bot 統計*

*リアクション統計:*
• 総数: {metrics['total_reactions']}
• 成功: {metrics['successful_reactions']}
• 失敗: {metrics['failed_reactions']}
• 成功率: {metrics['success_rate']:.1f}%
• リトライ実行回数: {metrics['retries_performed']}

*設定:*
• 最大リトライ: {metrics['configuration']['max_retries']}
• ベース遅延: {metrics['configuration']['base_delay']}秒
• 最大バックオフ: {metrics['configuration']['max_backoff_delay']}秒
• 並行制限: {metrics['configuration']['concurrent_limit']}
            """
            await respond({"text": metrics_text.strip()})
        except Exception as e:
            logger.error(f"Error getting emoji metrics: {e}")
            await respond({"text": "統計取得中にエラーが発生しました。"})

    async def open_modal(self, trigger_id: str, modal: Dict[str, Any]) -> None:
        """
        モーダルを開く

        Args:
            trigger_id: トリガーID
            modal: モーダル定義
        """
        await self.app.client.views_open(trigger_id=trigger_id, view=modal)

    async def update_message(
        self,
        channel: str,
        timestamp: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        メッセージを更新

        Args:
            channel: チャンネルID
            timestamp: メッセージタイムスタンプ
            text: 更新するテキスト
            blocks: オプションのブロック要素
        """
        await self.app.client.chat_update(
            channel=channel, ts=timestamp, text=text, blocks=blocks
        )

    async def send_ephemeral_message(
        self,
        channel: str,
        user: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        エフェメラルメッセージを送信

        Args:
            channel: チャンネルID
            user: ユーザーID
            text: メッセージテキスト
            blocks: オプションのブロック要素
        """
        await self.app.client.chat_postEphemeral(
            channel=channel, user=user, text=text, blocks=blocks
        )

    async def open_confirm_dialog(
        self, trigger_id: str, title: str, message: str
    ) -> None:
        """
        確認ダイアログを開く

        Args:
            trigger_id: トリガーID
            title: ダイアログタイトル
            message: 確認メッセージ
        """
        confirm_modal = {
            "type": "modal",
            "callback_id": "confirm_dialog",
            "title": {"type": "plain_text", "text": title},
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": message}}
            ],
            "submit": {"type": "plain_text", "text": "Confirm"},
            "close": {"type": "plain_text", "text": "Cancel"},
        }
        await self.open_modal(trigger_id, confirm_modal)

    async def register_view_submission_handler(self, callback_id: str, handler) -> None:
        """
        ビュー送信ハンドラーを登録

        Args:
            callback_id: コールバックID
            handler: ハンドラー関数
        """

        @self.app.view(callback_id)
        async def view_submission_handler(ack, body, view):
            await ack()
            await handler(body)

    async def register_action_handler(self, action_id: str, handler) -> None:
        """
        アクションハンドラーを登録

        Args:
            action_id: アクションID
            handler: ハンドラー関数
        """

        @self.app.action(action_id)
        async def action_handler(ack, body, action):
            await ack()
            await handler(body)

    async def post_message_with_blocks(
        self, channel: str, text: str, blocks: List[Dict[str, Any]]
    ) -> None:
        """
        ブロック付きメッセージを投稿

        Args:
            channel: チャンネルID
            text: フォールバックテキスト
            blocks: ブロック要素のリスト
        """
        await self.app.client.chat_postMessage(
            channel=channel, text=text, blocks=blocks
        )

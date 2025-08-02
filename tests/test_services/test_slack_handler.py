"""
SlackHandler単体テスト - TDD RED Phase

このテストは実装前に書かれており、最初は失敗することが期待されます。
SlackHandlerの期待される動作を定義します。
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch


class TestSlackHandler:
    """SlackHandlerクラスの単体テスト"""

    @pytest.fixture
    def mock_openai_service(self):
        """OpenAIServiceのモック"""
        service = AsyncMock()
        service.get_embedding = AsyncMock(return_value=[0.1] * 1536)
        return service

    @pytest.fixture
    def mock_emoji_service(self):
        """EmojiServiceのモック"""
        service = AsyncMock()
        service.find_similar_emojis = AsyncMock(
            return_value=[
                {"code": ":smile:", "description": "Happy expression"},
                {"code": ":thumbsup:", "description": "Approval"},
                {"code": ":heart:", "description": "Love"},
            ]
        )
        return service

    @pytest.fixture
    def mock_slack_app(self):
        """Slack Bolt Appのモック"""
        app = Mock()
        app.client = Mock()
        app.client.reactions_add = AsyncMock()
        return app

    @pytest.fixture
    def slack_handler(self, mock_openai_service, mock_emoji_service):
        """SlackHandlerインスタンス（実装後に有効化）"""
        with patch("app.services.slack_handler.App") as mock_app_class, patch(
            "app.services.slack_handler.SocketModeHandler"
        ) as mock_socket_handler_class, patch(
            "app.services.slack_handler.Config"
        ) as mock_config_class:

            # Mock App instance
            mock_app = Mock()
            mock_client = Mock()
            mock_client.reactions_add = Mock(return_value={"ok": True})
            mock_app.client = mock_client
            mock_app.event = Mock(return_value=lambda func: func)
            mock_app_class.return_value = mock_app

            # Mock SocketModeHandler instance
            mock_socket_handler = Mock()
            mock_socket_handler.start = Mock()
            mock_socket_handler.close = Mock()
            mock_socket_handler_class.return_value = mock_socket_handler

            # Mock Config instance
            mock_config = Mock()
            mock_config.slack.bot_token = "xoxb-test-token"
            mock_config.slack.app_token = "xapp-test-token"
            mock_config_class.return_value = mock_config

            from app.services.slack_handler import SlackHandler

            handler = SlackHandler(mock_openai_service, mock_emoji_service)

            # Inject the mocked app to the handler for test assertions
            handler.app = mock_app
            handler.socket_mode_handler = mock_socket_handler

            return handler

    def test_slack_handler_initialization(
        self, mock_openai_service, mock_emoji_service
    ):
        """SlackHandlerの初期化テスト"""
        with patch("app.services.slack_handler.App") as mock_app_class, patch(
            "app.services.slack_handler.SocketModeHandler"
        ) as mock_socket_handler_class, patch(
            "app.services.slack_handler.Config"
        ) as mock_config_class:

            # Mock Config
            mock_config = Mock()
            mock_config.slack.bot_token = "xoxb-test-token"
            mock_config.slack.app_token = "xapp-test-token"
            mock_config_class.return_value = mock_config

            # Mock App
            mock_app = Mock()
            mock_app.event = Mock(return_value=lambda func: func)
            mock_app_class.return_value = mock_app

            # Mock SocketModeHandler
            mock_socket_handler = Mock()
            mock_socket_handler_class.return_value = mock_socket_handler

            from app.services.slack_handler import SlackHandler

            handler = SlackHandler(mock_openai_service, mock_emoji_service)

            # 依存関係が正しく設定されることを確認
            assert handler.openai_service == mock_openai_service
            assert handler.emoji_service == mock_emoji_service
            assert handler.app is not None  # Slack Bolt appが初期化される
            assert handler.socket_mode_handler is not None

    @pytest.mark.asyncio
    async def test_handle_message_with_valid_message(
        self, slack_handler, sample_slack_message
    ):
        """有効なメッセージの処理テスト"""
        # メッセージ処理が正常に実行されることを確認
        await slack_handler.handle_message(sample_slack_message)

        # OpenAIServiceが呼び出されることを確認
        slack_handler.openai_service.get_embedding.assert_called_once_with(
            sample_slack_message["text"]
        )

        # EmojiServiceが呼び出されることを確認
        slack_handler.emoji_service.find_similar_emojis.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_filters_bot_messages(self, slack_handler):
        """Botメッセージのフィルタリングテスト"""
        bot_message = {
            "type": "message",
            "text": "Bot message",
            "user": "USLACKBOT",  # Slack botのユーザーID
            "channel": "C123456789",
            "ts": "1234567890.123456",
        }

        # Botメッセージは処理されないことを確認
        await slack_handler.handle_message(bot_message)

        # OpenAIServiceが呼び出されないことを確認
        slack_handler.openai_service.get_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_filters_own_bot_messages(self, slack_handler):
        """自分のBotメッセージのフィルタリングテスト"""
        # Bot自身のメッセージ
        own_bot_message = {
            "type": "message",
            "text": "My bot message",
            "bot_id": "B123456789",  # Bot ID
            "channel": "C123456789",
            "ts": "1234567890.123456",
        }

        # 自分のBotメッセージは処理されないことを確認
        await slack_handler.handle_message(own_bot_message)

        # OpenAIServiceが呼び出されないことを確認
        slack_handler.openai_service.get_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_reactions_success(self, slack_handler):
        """絵文字リアクション追加の成功テスト"""
        channel = "C123456789"
        timestamp = "1234567890.123456"
        emojis = [":smile:", ":thumbsup:", ":heart:"]

        # リアクション追加の実行
        await slack_handler.add_reactions(channel, timestamp, emojis)

        # Slack APIが適切に呼び出されることを確認
        assert slack_handler.app.client.reactions_add.call_count == 3

        # 各絵文字に対してAPIが呼び出されることを確認
        calls = slack_handler.app.client.reactions_add.call_args_list
        for i, emoji in enumerate(emojis):
            expected_call = {
                "channel": channel,
                "timestamp": timestamp,
                "name": emoji.strip(":"),
            }
            assert calls[i][1] == expected_call

    @pytest.mark.asyncio
    async def test_add_reactions_with_slack_api_error(self, slack_handler):
        """Slack API エラー時のテスト"""
        channel = "C123456789"
        timestamp = "1234567890.123456"
        emojis = [":smile:"]

        # Slack API エラーをシミュレート
        class MockSlackApiError(Exception):
            def __init__(self, message, response):
                super().__init__(message)
                self.response = response

        with patch("app.services.slack_handler.SlackApiError", MockSlackApiError):
            slack_handler.app.client.reactions_add = Mock(
                side_effect=MockSlackApiError("Error", {"error": "already_reacted"})
            )

        # エラーが適切にハンドリングされることを確認（例外が上がらない）
        try:
            await slack_handler.add_reactions(channel, timestamp, emojis)
        except Exception:
            pytest.fail("SlackApiError should be handled gracefully")

    @pytest.mark.asyncio
    async def test_handle_message_integration_flow(
        self, slack_handler, sample_slack_message
    ):
        """メッセージ処理の統合フローテスト"""
        # メッセージ処理の実行
        await slack_handler.handle_message(sample_slack_message)

        # 1. OpenAIServiceでベクトル化
        slack_handler.openai_service.get_embedding.assert_called_once_with(
            sample_slack_message["text"]
        )

        # 2. EmojiServiceで類似絵文字検索
        slack_handler.emoji_service.find_similar_emojis.assert_called_once()

        # 3. Slack APIでリアクション追加（3回）
        assert slack_handler.app.client.reactions_add.call_count == 3

    def test_slack_handler_socket_mode_configuration(self, slack_handler):
        """Socket Mode設定のテスト"""
        # Socket Mode アプリが正しく設定されることを確認
        assert hasattr(slack_handler, "socket_mode_handler")
        assert slack_handler.socket_mode_handler is not None

    @pytest.mark.asyncio
    async def test_handle_message_with_empty_text(self, slack_handler):
        """空のテキストメッセージの処理テスト"""
        empty_message = {
            "type": "message",
            "text": "",
            "user": "U123456789",
            "channel": "C123456789",
            "ts": "1234567890.123456",
        }

        # 空のメッセージは処理されないことを確認
        await slack_handler.handle_message(empty_message)

        # OpenAIServiceが呼び出されないことを確認
        slack_handler.openai_service.get_embedding.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_with_subtype_filtering(self, slack_handler):
        """サブタイプのあるメッセージのフィルタリングテスト"""
        # channel_joinメッセージなど、通常処理したくないメッセージ
        system_message = {
            "type": "message",
            "subtype": "channel_join",
            "text": "User joined the channel",
            "user": "U123456789",
            "channel": "C123456789",
            "ts": "1234567890.123456",
        }

        # システムメッセージは処理されないことを確認
        await slack_handler.handle_message(system_message)

        # OpenAIServiceが呼び出されないことを確認
        slack_handler.openai_service.get_embedding.assert_not_called()


class TestSlackHandlerReactionFeatures:
    """絵文字リアクション機能の詳細テスト (Task 1.3 RED Phase)"""

    @pytest.fixture
    def slack_handler_with_retry_capability(
        self, mock_openai_service, mock_emoji_service
    ):
        """リトライ機能を持つSlackHandler（実装されていないため失敗するはず）"""
        with patch("app.services.slack_handler.App") as mock_app_class, patch(
            "app.services.slack_handler.SocketModeHandler"
        ) as mock_socket_handler_class, patch(
            "app.services.slack_handler.Config"
        ) as mock_config_class:

            # Mock App instance
            mock_app = Mock()
            mock_client = Mock()
            mock_client.reactions_add = Mock(return_value={"ok": True})
            mock_app.client = mock_client
            mock_app.event = Mock(return_value=lambda func: func)
            mock_app_class.return_value = mock_app

            # Mock SocketModeHandler instance
            mock_socket_handler = Mock()
            mock_socket_handler.start = Mock()
            mock_socket_handler.close = Mock()
            mock_socket_handler_class.return_value = mock_socket_handler

            # Mock Config instance
            mock_config = Mock()
            mock_config.slack.bot_token = "xoxb-test-token"
            mock_config.slack.app_token = "xapp-test-token"
            mock_config_class.return_value = mock_config

            from app.services.slack_handler import SlackHandler

            handler = SlackHandler(mock_openai_service, mock_emoji_service)

            # Inject the mocked app to the handler for test assertions
            handler.app = mock_app
            handler.socket_mode_handler = mock_socket_handler

            return handler

    @pytest.mark.asyncio
    async def test_add_reactions_with_retry_logic(
        self, slack_handler_with_retry_capability
    ):
        """リトライ処理のテスト - このテストは失敗するはず（RED Phase）"""
        handler = slack_handler_with_retry_capability

        # レート制限エラーをシミュレート
        class MockRateLimitError(Exception):
            def __init__(self):
                self.response = {"error": "rate_limited"}

            def __str__(self):
                return "rate_limited"

        # 最初の2回は失敗、3回目は成功するようにモック設定
        call_count = 0

        def mock_reactions_add(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise MockRateLimitError()
            return {"ok": True}

        handler.app.client.reactions_add = Mock(side_effect=mock_reactions_add)

        # リトライ処理が実装されていない場合、このテストは失敗するはず
        await handler.add_reactions("C123456789", "1234567890.123456", [":smile:"])

        # 3回呼び出されることを期待（2回失敗 + 1回成功）
        # 現在の実装にはリトライがないため、このアサーションは失敗する
        assert (
            handler.app.client.reactions_add.call_count == 3
        ), "Retry logic should call reactions_add 3 times (2 failures + 1 success)"

    @pytest.mark.asyncio
    async def test_add_reactions_with_exponential_backoff(
        self, slack_handler_with_retry_capability
    ):
        """指数バックオフのテスト - このテストは失敗するはず（RED Phase）"""
        handler = slack_handler_with_retry_capability

        # 時間測定用のモック
        start_time = time.time()

        # レート制限エラーを発生させる
        class MockRateLimitError(Exception):
            def __init__(self):
                self.response = {"error": "rate_limited"}

            def __str__(self):
                return "rate_limited"

        handler.app.client.reactions_add = Mock(side_effect=MockRateLimitError())

        # 指数バックオフが実装されていない場合、このテストは失敗するはず
        await handler.add_reactions("C123456789", "1234567890.123456", [":smile:"])

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 指数バックオフが実装されていれば、少なくとも1秒は経過するはず
        # 現在の実装にはバックオフがないため、このアサーションは失敗する
        assert (
            elapsed_time >= 1.0
        ), "Exponential backoff should introduce delays between retries"

    @pytest.mark.asyncio
    async def test_add_reactions_max_retry_limit(
        self, slack_handler_with_retry_capability
    ):
        """最大リトライ回数の制限テスト - このテストは失敗するはず（RED Phase）"""
        handler = slack_handler_with_retry_capability

        # 常にエラーを発生させる
        class MockPersistentError(Exception):
            def __init__(self):
                self.response = {"error": "rate_limited"}

            def __str__(self):
                return "rate_limited"

        handler.app.client.reactions_add = Mock(side_effect=MockPersistentError())

        # 最大リトライ回数制限が実装されていない場合、このテストは失敗するはず
        await handler.add_reactions("C123456789", "1234567890.123456", [":smile:"])

        # 最大3回までリトライするはず（初回 + 2回リトライ）
        # 現在の実装にはリトライがないため、このアサーションは失敗する
        assert (
            handler.app.client.reactions_add.call_count <= 3
        ), "Should not retry more than maximum retry limit"

    @pytest.mark.asyncio
    async def test_add_reactions_concurrent_processing(
        self, slack_handler_with_retry_capability
    ):
        """同時並行処理のテスト - このテストは失敗するはず（RED Phase）"""
        handler = slack_handler_with_retry_capability

        # 複数の絵文字を同時に処理する時間を測定
        start_time = time.time()

        # 各リアクションに0.1秒の遅延を追加
        def mock_delayed_reaction(*args, **kwargs):
            time.sleep(0.1)  # 同期的なsleepを使用
            return {"ok": True}

        handler.app.client.reactions_add = Mock(side_effect=mock_delayed_reaction)

        # 5個の絵文字を処理
        emojis = [":smile:", ":thumbsup:", ":heart:", ":fire:", ":star:"]
        await handler.add_reactions("C123456789", "1234567890.123456", emojis)

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 並行処理が実装されていれば、0.5秒より短い時間で完了するはず
        # 現在の実装は逐次処理のため、このアサーションは失敗する
        assert elapsed_time < 0.3, (
            f"Concurrent processing should complete faster than sequential "
            f"(took {elapsed_time:.2f}s)"
        )

    @pytest.mark.asyncio
    async def test_add_reactions_with_rate_limit_monitoring(
        self, slack_handler_with_retry_capability
    ):
        """レート制限監視機能のテスト - このテストは失敗するはず（RED Phase）"""
        handler = slack_handler_with_retry_capability

        # レート制限ヘッダーをシミュレート
        class MockResponse:
            def __init__(self):
                self.headers = {
                    "X-Rate-Limit-Remaining": "10",
                    "X-Rate-Limit-Reset": str(int(time.time()) + 60),
                }

        handler.app.client.reactions_add = Mock(return_value=MockResponse())

        # レート制限監視が実装されていない場合、このテストは失敗するはず
        await handler.add_reactions("C123456789", "1234567890.123456", [":smile:"])

        # レート制限情報が記録されることを期待
        # 現在の実装にはレート制限監視がないため、このアサーションは失敗する
        assert hasattr(
            handler, "rate_limit_info"
        ), "Rate limit monitoring should track API usage information"


class TestSlackHandlerErrorHandling:
    """SlackHandlerのエラーハンドリングテスト"""

    @pytest.fixture
    def slack_handler_with_error_services(self):
        """エラーを発生させるサービスを持つSlackHandler"""
        with patch("app.services.slack_handler.App") as mock_app_class, patch(
            "app.services.slack_handler.SocketModeHandler"
        ) as mock_socket_handler_class, patch(
            "app.services.slack_handler.Config"
        ) as mock_config_class:

            # Mock App instance
            mock_app = Mock()
            mock_client = Mock()
            mock_client.reactions_add = Mock(return_value={"ok": True})
            mock_app.client = mock_client
            mock_app.event = Mock(return_value=lambda func: func)
            mock_app_class.return_value = mock_app

            # Mock SocketModeHandler instance
            mock_socket_handler = Mock()
            mock_socket_handler.start = Mock()
            mock_socket_handler.close = Mock()
            mock_socket_handler_class.return_value = mock_socket_handler

            # Mock Config instance
            mock_config = Mock()
            mock_config.slack.bot_token = "xoxb-test-token"
            mock_config.slack.app_token = "xapp-test-token"
            mock_config_class.return_value = mock_config

            from app.services.slack_handler import SlackHandler

            # エラーを発生させるモックサービス
            openai_service = AsyncMock()
            openai_service.get_embedding.side_effect = Exception("OpenAI API Error")

            emoji_service = AsyncMock()
            emoji_service.find_similar_emojis.side_effect = Exception("Database Error")

            handler = SlackHandler(openai_service, emoji_service)
            handler.app = mock_app
            handler.socket_mode_handler = mock_socket_handler

            return handler

    @pytest.mark.asyncio
    async def test_handle_message_with_openai_error(
        self, slack_handler_with_error_services, sample_slack_message
    ):
        """OpenAI APIエラー時の処理テスト"""
        # OpenAI APIエラーが発生しても例外が上がらないことを確認
        try:
            await slack_handler_with_error_services.handle_message(sample_slack_message)
        except Exception:
            pytest.fail("OpenAI API error should be handled gracefully")

    @pytest.mark.asyncio
    async def test_handle_message_with_emoji_service_error(
        self, slack_handler_with_error_services, sample_slack_message
    ):
        """EmojiServiceエラー時の処理テスト"""
        # データベースエラーが発生しても例外が上がらないことを確認
        try:
            await slack_handler_with_error_services.handle_message(sample_slack_message)
        except Exception:
            pytest.fail("Database error should be handled gracefully")

"""
ベクトル化コマンドのテスト

/emoji vectorizeコマンドの動作を検証
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.admin_user import Permission
from app.services.slash_command_handler import SlashCommandHandler
from app.services.modal_handler import ModalHandler


class TestVectorizationCommand:
    """ベクトル化コマンドのテストクラス"""

    @pytest.fixture
    def mock_permission_manager(self):
        """PermissionManagerのモック"""
        manager = AsyncMock()
        manager.check_permission = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def mock_emoji_service(self):
        """EmojiServiceのモック"""
        service = AsyncMock()
        service.count_emojis = AsyncMock(return_value=50)
        service.get_all_emojis = AsyncMock(return_value=[])
        service.vectorize_all_emojis = AsyncMock(
            return_value={
                "processed": 45,
                "skipped": 5,
                "filtered_out": 0,
                "total": 50,
            }
        )
        return service

    @pytest.fixture
    def mock_slack_handler(self):
        """SlackHandlerのモック"""
        handler = AsyncMock()
        handler.open_modal = AsyncMock()
        handler.send_ephemeral_message = AsyncMock()
        handler.update_message = AsyncMock()
        handler.post_message_with_blocks = AsyncMock()
        return handler

    @pytest.fixture
    def modal_handler(self):
        """ModalHandlerインスタンス"""
        return ModalHandler()

    @pytest.fixture
    def command_handler(
        self, mock_permission_manager, mock_emoji_service, mock_slack_handler
    ):
        """SlashCommandHandlerインスタンス"""
        handler = SlashCommandHandler(
            permission_manager=mock_permission_manager,
            emoji_service=mock_emoji_service,
            slack_handler=mock_slack_handler,
        )
        handler.modal_handler = ModalHandler()
        return handler

    @pytest.mark.asyncio
    async def test_vectorize_command_opens_confirmation_dialog(
        self, command_handler, mock_slack_handler, mock_emoji_service
    ):
        """vectorizeコマンドが確認ダイアログを開くことを確認"""
        # テストデータ
        payload = {
            "user_id": "U123456",
            "text": "vectorize",
            "trigger_id": "trigger123",
        }

        # 実行
        response = await command_handler.handle_emoji_command(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert "Opening vectorization confirmation" in response["text"]

        # モーダルが開かれたことを確認
        mock_slack_handler.open_modal.assert_called_once()
        call_args = mock_slack_handler.open_modal.call_args
        assert call_args[0][0] == "trigger123"  # trigger_id
        modal = call_args[0][1]
        assert modal["callback_id"] == "vectorize_confirm_modal"
        assert "50 emojis" in modal["blocks"][0]["text"]["text"]

    @pytest.mark.asyncio
    async def test_vectorize_command_requires_admin_permission(
        self, command_handler, mock_permission_manager
    ):
        """vectorizeコマンドが管理者権限を要求することを確認"""
        # 権限不足を設定
        mock_permission_manager.check_permission = AsyncMock(return_value=False)

        # テストデータ
        payload = {
            "user_id": "U123456",
            "text": "vectorize",
            "trigger_id": "trigger123",
        }

        # 実行
        response = await command_handler.handle_emoji_command(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert "permission denied" in response["text"].lower()

        # 管理者権限がチェックされたことを確認
        mock_permission_manager.check_permission.assert_called_with(
            "U123456", Permission.ADMIN
        )

    @pytest.mark.asyncio
    async def test_vectorize_confirm_action_starts_vectorization(
        self, command_handler, mock_emoji_service, mock_slack_handler
    ):
        """確認ダイアログのConfirmボタンがベクトル化を開始することを確認"""
        # モックの設定
        mock_task = AsyncMock()
        mock_task.cancelled = MagicMock(return_value=False)

        # asyncio.create_taskをモック
        with patch("asyncio.create_task", return_value=mock_task):
            # アクションペイロード
            payload = {
                "type": "block_actions",
                "user": {"id": "U123456"},
                "actions": [{"action_id": "vectorize_confirm"}],
                "response_url": "https://slack.com/response",
            }

            # 実行
            await command_handler.handle_action(payload)

            # 即座の応答を確認
            mock_slack_handler.send_ephemeral_message.assert_called()
            call_args = mock_slack_handler.send_ephemeral_message.call_args
            assert "Vectorization started" in call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_vectorize_cancel_action(self, command_handler, mock_slack_handler):
        """確認ダイアログのCancelボタンの動作を確認"""
        # アクションペイロード
        payload = {
            "type": "block_actions",
            "user": {"id": "U123456"},
            "actions": [{"action_id": "vectorize_cancel"}],
            "response_url": "https://slack.com/response",
        }

        # 実行
        await command_handler.handle_action(payload)

        # キャンセルメッセージを確認
        mock_slack_handler.send_ephemeral_message.assert_called()
        call_args = mock_slack_handler.send_ephemeral_message.call_args
        assert "cancelled" in call_args[1]["text"].lower()

    @pytest.mark.asyncio
    async def test_vectorize_command_with_options(
        self, command_handler, mock_slack_handler
    ):
        """vectorizeコマンドのオプション指定を確認"""
        # テストデータ（skip_existingオプション付き）
        payload = {
            "user_id": "U123456",
            "text": "vectorize --skip-existing",
            "trigger_id": "trigger123",
        }

        # 実行
        response = await command_handler.handle_emoji_command(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert "skip existing" in response["text"].lower()

    @pytest.mark.asyncio
    async def test_vectorization_progress_reporting(
        self, command_handler, mock_emoji_service, mock_slack_handler
    ):
        """ベクトル化の進捗報告を確認"""

        # プログレスコールバックを設定
        async def mock_vectorize_all_emojis(**kwargs):
            # プログレスコールバックを呼び出す
            if "progress_callback" in kwargs and kwargs["progress_callback"]:
                await kwargs["progress_callback"](10, 50, ":smile:")
                await kwargs["progress_callback"](25, 50, ":heart:")
                await kwargs["progress_callback"](50, 50, ":thumbsup:")

            return {
                "processed": 50,
                "skipped": 0,
                "filtered_out": 0,
                "total": 50,
            }

        mock_emoji_service.vectorize_all_emojis = mock_vectorize_all_emojis

        # ベクトル化タスクを直接実行
        await command_handler._run_vectorization_task(
            "U123456", "https://slack.com/response", {}
        )

        # 進捗メッセージが送信されたことを確認
        assert mock_slack_handler.post_message_with_blocks.call_count >= 2

    @pytest.mark.asyncio
    async def test_vectorization_error_handling(
        self, command_handler, mock_emoji_service, mock_slack_handler
    ):
        """ベクトル化エラー時の処理を確認"""
        # エラーを発生させる
        mock_emoji_service.vectorize_all_emojis = AsyncMock(
            side_effect=Exception("OpenAI API error")
        )

        # ベクトル化タスクを実行
        await command_handler._run_vectorization_task(
            "U123456", "https://slack.com/response", {}
        )

        # エラーメッセージが送信されたことを確認
        mock_slack_handler.post_message_with_blocks.assert_called()
        call_args = mock_slack_handler.post_message_with_blocks.call_args
        blocks = call_args[1]["blocks"]

        # エラーメッセージを含むブロックを確認
        error_found = False
        for block in blocks:
            if block.get("type") == "section" and "text" in block:
                if "error" in block["text"].get("text", "").lower():
                    error_found = True
                    break
        assert error_found

    @pytest.mark.asyncio
    async def test_vectorization_dry_run(
        self, command_handler, mock_emoji_service, mock_slack_handler
    ):
        """ドライラン機能のテスト"""
        # ドライラン結果を設定
        mock_emoji_service.vectorize_all_emojis = AsyncMock(
            return_value={
                "dry_run": True,
                "would_process": 30,
                "skipped": 20,
                "filtered_out": 0,
            }
        )

        # テストデータ
        payload = {
            "user_id": "U123456",
            "text": "vectorize --dry-run",
            "trigger_id": "trigger123",
        }

        # 実行
        response = await command_handler.handle_emoji_command(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert "dry run" in response["text"].lower()

    def test_create_vectorization_progress_blocks(self, modal_handler):
        """進捗表示ブロックの作成を確認"""
        # 進捗情報
        progress = {
            "current": 25,
            "total": 100,
            "percentage": 25,
            "emoji_code": ":smile:",
        }

        # ブロック作成
        blocks = modal_handler.create_vectorization_progress_blocks(progress)

        # 検証
        assert len(blocks) >= 2
        assert any("25%" in str(block) for block in blocks)
        assert any(":smile:" in str(block) for block in blocks)

    def test_create_vectorization_result_blocks(self, modal_handler):
        """結果表示ブロックの作成を確認"""
        # 結果情報
        result = {
            "processed": 45,
            "skipped": 5,
            "filtered_out": 0,
            "total": 50,
            "duration": 120.5,
        }

        # ブロック作成
        blocks = modal_handler.create_vectorization_result_blocks(result)

        # 検証
        assert len(blocks) >= 2
        assert any("45" in str(block) for block in blocks)
        assert any("120.5" in str(block) for block in blocks)

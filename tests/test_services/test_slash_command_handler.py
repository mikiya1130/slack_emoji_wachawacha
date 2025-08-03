"""
スラッシュコマンドハンドラーのテスト

/emojiコマンドのルーティングと権限チェックのテスト
"""

import pytest
from unittest.mock import Mock, AsyncMock

from app.services.slash_command_handler import SlashCommandHandler
from app.models.admin_user import Permission
from app.utils.permission_manager import PermissionManager


class TestSlashCommandHandler:
    """SlashCommandHandlerのテストクラス"""

    @pytest.fixture
    def mock_slack_handler(self):
        """モックSlackHandler"""
        return Mock()

    @pytest.fixture
    def mock_emoji_service(self):
        """モックEmojiService"""
        return Mock()

    @pytest.fixture
    def mock_permission_manager(self):
        """モックPermissionManager"""
        return Mock(spec=PermissionManager)

    @pytest.fixture
    def slash_command_handler(
        self, mock_slack_handler, mock_emoji_service, mock_permission_manager
    ):
        """SlashCommandHandlerインスタンス"""
        return SlashCommandHandler(
            slack_handler=mock_slack_handler,
            emoji_service=mock_emoji_service,
            permission_manager=mock_permission_manager,
        )

    @pytest.fixture
    def mock_command_payload(self):
        """スラッシュコマンドのペイロード"""
        return {
            "user_id": "U123456",
            "user_name": "test_user",
            "team_id": "T123456",
            "team_domain": "test_team",
            "channel_id": "C123456",
            "channel_name": "test_channel",
            "command": "/emoji",
            "text": "",
            "response_url": "https://hooks.slack.com/commands/T123456/123456",
            "trigger_id": "123456.123456.abcdef",
        }

    @pytest.mark.asyncio
    async def test_handle_emoji_command_help(
        self, slash_command_handler, mock_command_payload
    ):
        """ヘルプコマンドのテスト"""
        mock_command_payload["text"] = "help"

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert "Available commands:" in response["text"]
        assert "/emoji list" in response["text"]
        assert "/emoji add" in response["text"]
        assert "/emoji search" in response["text"]

    @pytest.mark.asyncio
    async def test_handle_emoji_command_list(
        self,
        slash_command_handler,
        mock_command_payload,
        mock_emoji_service,
        mock_permission_manager,
    ):
        """listコマンドのテスト（VIEWER権限）"""
        mock_command_payload["text"] = "list"
        mock_permission_manager.check_permission = AsyncMock(return_value=True)
        mock_emoji_service.get_all_emojis = AsyncMock(
            return_value=[
                Mock(code=":smile:", description="Smiling face", category="emotions"),
                Mock(code=":thumbsup:", description="Thumbs up", category="gestures"),
            ]
        )

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert ":smile:" in response["text"]
        assert ":thumbsup:" in response["text"]
        mock_permission_manager.check_permission.assert_called_once_with(
            "U123456", Permission.VIEWER
        )

    @pytest.mark.asyncio
    async def test_handle_emoji_command_add_modal(
        self,
        slash_command_handler,
        mock_command_payload,
        mock_permission_manager,
        mock_slack_handler,
    ):
        """addコマンドのテスト（モーダル表示）"""
        mock_command_payload["text"] = "add"
        mock_permission_manager.check_permission = AsyncMock(return_value=True)
        mock_slack_handler.open_modal = AsyncMock(return_value=True)

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert "Opening emoji add form" in response["text"]
        mock_permission_manager.check_permission.assert_called_once_with(
            "U123456", Permission.EDITOR
        )
        mock_slack_handler.open_modal.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_emoji_command_search(
        self, slash_command_handler, mock_command_payload, mock_emoji_service
    ):
        """searchコマンドのテスト"""
        mock_command_payload["text"] = "search happy"
        mock_emoji_service.search_emojis = AsyncMock(
            return_value=[
                Mock(code=":smile:", description="Happy smiling face"),
                Mock(code=":joy:", description="Tears of joy, very happy"),
            ]
        )

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert "Search results for 'happy':" in response["text"]
        assert ":smile:" in response["text"]
        assert ":joy:" in response["text"]

    @pytest.mark.asyncio
    async def test_handle_emoji_command_delete(
        self,
        slash_command_handler,
        mock_command_payload,
        mock_permission_manager,
        mock_emoji_service,
    ):
        """deleteコマンドのテスト（EDITOR権限）"""
        mock_command_payload["text"] = "delete :custom_emoji:"
        mock_permission_manager.check_permission = AsyncMock(return_value=True)
        mock_emoji_service.delete_emoji_by_code = AsyncMock(return_value=True)

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert "Emoji :custom_emoji: deleted successfully" in response["text"]
        mock_permission_manager.check_permission.assert_called_once_with(
            "U123456", Permission.EDITOR
        )

    @pytest.mark.asyncio
    async def test_handle_emoji_command_vectorize_confirm(
        self,
        slash_command_handler,
        mock_command_payload,
        mock_permission_manager,
        mock_slack_handler,
        mock_emoji_service,
    ):
        """vectorizeコマンドのテスト（確認ダイアログ）"""
        mock_command_payload["text"] = "vectorize"
        mock_permission_manager.check_permission = AsyncMock(return_value=True)
        mock_emoji_service.count_emojis = AsyncMock(return_value=42)
        mock_slack_handler.open_modal = AsyncMock(return_value=True)

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert "Opening vectorization confirmation" in response["text"]
        mock_permission_manager.check_permission.assert_called_once_with(
            "U123456", Permission.ADMIN
        )
        mock_slack_handler.open_modal.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_emoji_command_stats(
        self, slash_command_handler, mock_command_payload, mock_emoji_service
    ):
        """statsコマンドのテスト"""
        mock_command_payload["text"] = "stats"
        mock_emoji_service.get_emoji_stats = AsyncMock(
            return_value={
                "total": 150,
                "by_category": {
                    "emotions": 50,
                    "gestures": 30,
                    "objects": 40,
                    "symbols": 30,
                },
                "vectorized": 120,
                "not_vectorized": 30,
            }
        )

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert "Emoji Statistics" in response["text"]
        assert "Total emojis: 150" in response["text"]
        assert "Vectorized: 120" in response["text"]

    @pytest.mark.asyncio
    async def test_handle_emoji_command_permission_denied(
        self, slash_command_handler, mock_command_payload, mock_permission_manager
    ):
        """権限不足エラーのテスト"""
        mock_command_payload["text"] = "add"
        mock_permission_manager.check_permission = AsyncMock(return_value=False)

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert "Permission denied" in response["text"]
        assert "EDITOR permission required" in response["text"]

    @pytest.mark.asyncio
    async def test_handle_emoji_command_invalid_subcommand(
        self, slash_command_handler, mock_command_payload
    ):
        """無効なサブコマンドのテスト"""
        mock_command_payload["text"] = "invalid_command"

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert "Unknown command: invalid_command" in response["text"]
        assert "Use '/emoji help'" in response["text"]

    @pytest.mark.asyncio
    async def test_handle_emoji_command_error_handling(
        self, slash_command_handler, mock_command_payload, mock_emoji_service
    ):
        """エラーハンドリングのテスト"""
        mock_command_payload["text"] = "list"
        mock_emoji_service.get_all_emojis = AsyncMock(
            side_effect=Exception("Database connection error")
        )

        response = await slash_command_handler.handle_emoji_command(
            mock_command_payload
        )

        assert response["response_type"] == "ephemeral"
        assert "An error occurred" in response["text"]
        assert "Please try again later" in response["text"]

    @pytest.mark.asyncio
    async def test_parse_command_text(self, slash_command_handler):
        """コマンドテキスト解析のテスト"""
        # サブコマンドのみ
        subcommand, args = slash_command_handler.parse_command_text("list")
        assert subcommand == "list"
        assert args == []

        # サブコマンドと引数
        subcommand, args = slash_command_handler.parse_command_text(
            "search happy emoji"
        )
        assert subcommand == "search"
        assert args == ["happy", "emoji"]

        # 空のコマンド
        subcommand, args = slash_command_handler.parse_command_text("")
        assert subcommand == "help"
        assert args == []

    @pytest.mark.asyncio
    async def test_handle_modal_submission(
        self, slash_command_handler, mock_emoji_service
    ):
        """モーダル送信処理のテスト"""
        mock_payload = {
            "user": {"id": "U123456"},
            "view": {
                "state": {
                    "values": {
                        "emoji_code": {"emoji_code_input": {"value": ":custom:"}},
                        "description": {"description_input": {"value": "Custom emoji"}},
                        "category": {
                            "category_select": {"selected_option": {"value": "objects"}}
                        },
                        "emotion_tone": {
                            "emotion_select": {"selected_option": {"value": "neutral"}}
                        },
                        "usage_scene": {"usage_input": {"value": "general"}},
                        "priority": {"priority_input": {"value": "1"}},
                    }
                }
            },
        }

        mock_emoji_service.create_emoji = AsyncMock(return_value=True)

        response = await slash_command_handler.handle_emoji_add_submission(mock_payload)

        assert response["response_type"] == "ephemeral"
        assert "Emoji :custom: added successfully" in response["text"]
        mock_emoji_service.create_emoji.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_vectorization_confirmation(
        self, slash_command_handler, mock_emoji_service
    ):
        """ベクトル化確認処理のテスト"""
        mock_payload = {
            "user": {"id": "U123456"},
            "actions": [{"action_id": "vectorize_confirm", "value": "confirm"}],
        }

        mock_emoji_service.vectorize_all_emojis = AsyncMock(
            return_value={"total": 50, "success": 48, "failed": 2}
        )

        response = await slash_command_handler.handle_vectorization_action(mock_payload)

        assert "Vectorization started" in response["text"]
        assert "Total: 50" in response["text"]
        assert "Success: 48" in response["text"]

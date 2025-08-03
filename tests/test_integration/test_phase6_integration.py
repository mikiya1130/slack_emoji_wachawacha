"""
Phase 6 統合テスト

スラッシュコマンド機能の統合テスト
"""

import pytest
from unittest.mock import AsyncMock

from app.models.admin_user import AdminUser, Permission
from app.models.emoji import EmojiData
from app.services.slash_command_handler import SlashCommandHandler
from app.services.modal_handler import ModalHandler, EmojiFormData
from app.services.emoji_service import EmojiService
from app.utils.permission_manager import PermissionManager


class TestPhase6Integration:
    """Phase 6機能の統合テストクラス"""

    @pytest.fixture
    def mock_database_service(self):
        """DatabaseServiceのモック"""
        service = AsyncMock()
        service.get_admin_user = AsyncMock(return_value=None)
        service.save_admin_user = AsyncMock(return_value=True)
        service.get_all_emojis = AsyncMock(return_value=[])
        service.count_emojis = AsyncMock(return_value=0)
        service.delete_emoji = AsyncMock(return_value=True)
        service.get_emoji_by_code = AsyncMock(return_value=None)
        service.insert_emoji = AsyncMock()
        return service

    @pytest.fixture
    def emoji_service(self, mock_database_service):
        """EmojiServiceインスタンス"""
        service = EmojiService(
            database_service=mock_database_service,
            cache_enabled=True,
        )
        return service

    @pytest.fixture
    def permission_manager(self, mock_database_service):
        """PermissionManagerインスタンス"""
        return PermissionManager(db_service=mock_database_service)

    @pytest.fixture
    def slack_handler(self):
        """SlackHandlerのモック"""
        handler = AsyncMock()
        handler.open_modal = AsyncMock()
        handler.send_ephemeral_message = AsyncMock()
        handler.post_message_with_blocks = AsyncMock()
        return handler

    @pytest.fixture
    def slash_command_handler(self, slack_handler, emoji_service, permission_manager):
        """SlashCommandHandlerインスタンス"""
        return SlashCommandHandler(
            slack_handler=slack_handler,
            emoji_service=emoji_service,
            permission_manager=permission_manager,
        )

    @pytest.mark.asyncio
    async def test_full_command_flow_list(
        self,
        slash_command_handler,
        mock_database_service,
    ):
        """リストコマンドの完全なフローをテスト"""
        # サンプル絵文字データ
        sample_emojis = [
            EmojiData(
                id=1,
                code=":smile:",
                description="Smiling face",
                category="emotions",
            ),
            EmojiData(
                id=2,
                code=":wave:",
                description="Waving hand",
                category="gestures",
            ),
        ]
        mock_database_service.get_all_emojis = AsyncMock(return_value=sample_emojis)

        # コマンドペイロード
        payload = {
            "user_id": "U123456",
            "text": "list",
            "trigger_id": "trigger123",
            "channel_id": "C123456",
        }

        # 実行
        response = await slash_command_handler.handle_emoji_command(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert "2 emojis sent in 1 message" in response["text"]

    @pytest.mark.asyncio
    async def test_permission_flow_admin_only(
        self,
        slash_command_handler,
        mock_database_service,
        slack_handler,
    ):
        """管理者権限が必要なコマンドのフローをテスト"""
        # 管理者ユーザーを設定
        admin_user = AdminUser(
            user_id="U123456",
            username="admin_user",
            permission=Permission.ADMIN,
        )
        mock_database_service.get_admin_user = AsyncMock(return_value=admin_user)
        mock_database_service.count_emojis = AsyncMock(return_value=50)

        # コマンドペイロード
        payload = {
            "user_id": "U123456",
            "text": "vectorize",
            "trigger_id": "trigger123",
        }

        # 実行
        response = await slash_command_handler.handle_emoji_command(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert "Opening vectorization confirmation" in response["text"]
        slack_handler.open_modal.assert_called_once()

    @pytest.mark.asyncio
    async def test_modal_submission_flow(
        self,
        slash_command_handler,
        mock_database_service,
    ):
        """モーダル送信フローをテスト"""
        # モーダル送信ペイロード
        payload = {
            "view": {
                "state": {
                    "values": {
                        "emoji_code": {"emoji_code_input": {"value": ":custom:"}},
                        "description": {"description_input": {"value": "Custom emoji"}},
                        "category": {
                            "category_select": {"selected_option": {"value": "custom"}}
                        },
                        "emotion_tone": {
                            "emotion_select": {"selected_option": {"value": "neutral"}}
                        },
                        "usage_scene": {"usage_input": {"value": "general"}},
                        "priority": {"priority_input": {"value": "5"}},
                    }
                }
            }
        }

        # 実行
        response = await slash_command_handler.handle_emoji_add_submission(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert ":custom:" in response["text"]
        assert "successfully" in response["text"]

    @pytest.mark.asyncio
    async def test_search_command_flow(
        self,
        slash_command_handler,
        emoji_service,
        mock_database_service,
    ):
        """検索コマンドのフローをテスト"""
        # 検索結果のモック
        mock_database_service.get_all_emojis = AsyncMock(
            return_value=[
                EmojiData(
                    id=1,
                    code=":smile:",
                    description="Smiling face",
                    category="emotions",
                ),
                EmojiData(
                    id=2,
                    code=":happy:",
                    description="Happy face",
                    category="emotions",
                ),
            ]
        )

        # コマンドペイロード
        payload = {
            "user_id": "U123456",
            "channel_id": "C123456",
            "text": "search smile",
            "trigger_id": "trigger123",
        }

        # 実行
        response = await slash_command_handler.handle_emoji_command(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert "Found 1 emojis for 'smile'" in response["text"]

    @pytest.mark.asyncio
    async def test_stats_command_with_comprehensive_data(
        self,
        slash_command_handler,
        mock_database_service,
    ):
        """統計コマンドの包括的なテスト"""
        # 複雑な絵文字データセット
        emojis = []
        for i in range(100):
            emoji = EmojiData(
                id=i,
                code=f":emoji_{i}:",
                description=f"Emoji {i}",
                category=["emotions", "gestures", "objects", "symbols"][i % 4],
                emotion_tone=["positive", "negative", "neutral"][i % 3],
                embedding=[0.1] * 1536 if i % 5 != 0 else None,  # 80%がベクトル化済み
            )
            emojis.append(emoji)

        mock_database_service.get_all_emojis = AsyncMock(return_value=emojis)

        # コマンドペイロード
        payload = {
            "user_id": "U123456",
            "text": "stats",
            "trigger_id": "trigger123",
        }

        # 実行
        response = await slash_command_handler.handle_emoji_command(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert "Total emojis: 100" in response["text"]
        assert "Vectorized: 80" in response["text"]
        assert "Not vectorized: 20" in response["text"]
        assert "emotions: 25" in response["text"]
        assert "gestures: 25" in response["text"]

    @pytest.mark.asyncio
    async def test_error_handling_flow(
        self,
        slash_command_handler,
        mock_database_service,
    ):
        """エラーハンドリングのフローをテスト"""
        # データベースエラーをシミュレート
        mock_database_service.get_all_emojis = AsyncMock(
            side_effect=Exception("Database connection error")
        )

        # コマンドペイロード
        payload = {
            "user_id": "U123456",
            "channel_id": "C123456",
            "text": "list",
            "trigger_id": "trigger123",
        }

        # 実行
        response = await slash_command_handler.handle_emoji_command(payload)

        # 検証
        assert response["response_type"] == "ephemeral"
        assert "error occurred" in response["text"].lower()

    @pytest.mark.asyncio
    async def test_permission_inheritance(
        self,
        permission_manager,
        mock_database_service,
    ):
        """権限継承のテスト"""
        # 異なる権限レベルのユーザーを作成
        admin = AdminUser("U001", "admin", Permission.ADMIN)
        editor = AdminUser("U002", "editor", Permission.EDITOR)
        viewer = AdminUser("U003", "viewer", Permission.VIEWER)

        # モックの設定
        mock_database_service.get_admin_user = AsyncMock(
            side_effect=lambda user_id: {
                "U001": admin,
                "U002": editor,
                "U003": viewer,
            }.get(user_id)
        )

        # 権限チェック
        # ADMIN > EDITOR > VIEWER
        assert await permission_manager.check_permission("U001", Permission.VIEWER)
        assert await permission_manager.check_permission("U001", Permission.EDITOR)
        assert await permission_manager.check_permission("U001", Permission.ADMIN)

        assert await permission_manager.check_permission("U002", Permission.VIEWER)
        assert await permission_manager.check_permission("U002", Permission.EDITOR)
        assert not await permission_manager.check_permission("U002", Permission.ADMIN)

        assert await permission_manager.check_permission("U003", Permission.VIEWER)
        assert not await permission_manager.check_permission("U003", Permission.EDITOR)
        assert not await permission_manager.check_permission("U003", Permission.ADMIN)

    def test_modal_validation_integration(self):
        """モーダルバリデーションの統合テスト"""
        modal_handler = ModalHandler()

        # 有効なフォームデータ
        valid_form = EmojiFormData(
            code=":valid_emoji:",
            description="Valid description",
            category="emotions",
            emotion_tone="positive",
            usage_scene="celebration",
            priority=5,
        )

        # バリデーション
        errors = modal_handler.validate_form_data(valid_form)
        assert len(errors) == 0

        # 無効なフォームデータ
        invalid_form = EmojiFormData(
            code="invalid_emoji",  # コロンがない
            description="",  # 空の説明
            category="emotions",
            emotion_tone="positive",
            usage_scene="celebration",
            priority=15,  # 範囲外
        )

        # バリデーション
        errors = modal_handler.validate_form_data(invalid_form)
        assert len(errors) == 3  # 3つのエラー
        assert any("emoji code" in error.lower() for error in errors)
        assert any("description" in error.lower() for error in errors)
        assert any("priority" in error.lower() for error in errors)

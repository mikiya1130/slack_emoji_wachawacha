"""
権限管理ユーティリティのテスト

スラッシュコマンドでの権限チェック機能のテスト
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, UTC

from app.utils.permission_manager import PermissionManager
from app.models.admin_user import AdminUser, Permission
from app.services.database_service import DatabaseService


class TestPermissionManager:
    """PermissionManagerのテストクラス"""

    @pytest.fixture
    def mock_db_service(self):
        """モックDatabaseServiceの作成"""
        return Mock(spec=DatabaseService)

    @pytest.fixture
    def permission_manager(self, mock_db_service):
        """PermissionManagerインスタンスの作成"""
        return PermissionManager(db_service=mock_db_service)

    @pytest.mark.asyncio
    async def test_check_permission_admin(self, permission_manager, mock_db_service):
        """管理者権限チェックのテスト"""
        # 管理者ユーザーのモック
        admin_user = AdminUser(
            user_id="U_ADMIN",
            username="admin_user",
            permission=Permission.ADMIN,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_db_service.get_admin_user = AsyncMock(return_value=admin_user)

        # 管理者権限チェック
        result = await permission_manager.check_permission("U_ADMIN", Permission.ADMIN)
        assert result is True

        # エディター権限チェック（管理者は全権限を持つ）
        result = await permission_manager.check_permission("U_ADMIN", Permission.EDITOR)
        assert result is True

        # ビューワー権限チェック（管理者は全権限を持つ）
        result = await permission_manager.check_permission("U_ADMIN", Permission.VIEWER)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_editor(self, permission_manager, mock_db_service):
        """エディター権限チェックのテスト"""
        # エディターユーザーのモック
        editor_user = AdminUser(
            user_id="U_EDITOR",
            username="editor_user",
            permission=Permission.EDITOR,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_db_service.get_admin_user = AsyncMock(return_value=editor_user)

        # 管理者権限チェック（エディターは管理者権限を持たない）
        result = await permission_manager.check_permission("U_EDITOR", Permission.ADMIN)
        assert result is False

        # エディター権限チェック
        result = await permission_manager.check_permission(
            "U_EDITOR", Permission.EDITOR
        )
        assert result is True

        # ビューワー権限チェック（エディターはビューワー権限も持つ）
        result = await permission_manager.check_permission(
            "U_EDITOR", Permission.VIEWER
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_viewer(self, permission_manager, mock_db_service):
        """ビューワー権限チェックのテスト"""
        # ビューワーユーザーのモック
        viewer_user = AdminUser(
            user_id="U_VIEWER",
            username="viewer_user",
            permission=Permission.VIEWER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_db_service.get_admin_user = AsyncMock(return_value=viewer_user)

        # 管理者権限チェック（ビューワーは管理者権限を持たない）
        result = await permission_manager.check_permission("U_VIEWER", Permission.ADMIN)
        assert result is False

        # エディター権限チェック（ビューワーはエディター権限を持たない）
        result = await permission_manager.check_permission(
            "U_VIEWER", Permission.EDITOR
        )
        assert result is False

        # ビューワー権限チェック
        result = await permission_manager.check_permission(
            "U_VIEWER", Permission.VIEWER
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_default_viewer(
        self, permission_manager, mock_db_service
    ):
        """デフォルトビューワー権限のテスト（ユーザーが登録されていない場合）"""
        # ユーザーが存在しない場合
        mock_db_service.get_admin_user = AsyncMock(return_value=None)

        # デフォルトでビューワー権限を持つ
        result = await permission_manager.check_permission(
            "U_NEW_USER", Permission.VIEWER
        )
        assert result is True

        # エディター権限は持たない
        result = await permission_manager.check_permission(
            "U_NEW_USER", Permission.EDITOR
        )
        assert result is False

        # 管理者権限は持たない
        result = await permission_manager.check_permission(
            "U_NEW_USER", Permission.ADMIN
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_add_admin_user(self, permission_manager, mock_db_service):
        """管理者ユーザー追加のテスト"""
        mock_db_service.save_admin_user = AsyncMock(return_value=True)

        result = await permission_manager.add_admin_user(
            user_id="U_NEW_ADMIN", username="new_admin", permission=Permission.ADMIN
        )
        assert result is True

        # save_admin_userが呼ばれたことを確認
        mock_db_service.save_admin_user.assert_called_once()
        call_args = mock_db_service.save_admin_user.call_args[0][0]
        assert isinstance(call_args, AdminUser)
        assert call_args.user_id == "U_NEW_ADMIN"
        assert call_args.username == "new_admin"
        assert call_args.permission == Permission.ADMIN

    @pytest.mark.asyncio
    async def test_update_permission(self, permission_manager, mock_db_service):
        """権限更新のテスト"""
        # 既存ユーザーのモック
        existing_user = AdminUser(
            user_id="U_EXISTING",
            username="existing_user",
            permission=Permission.VIEWER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_db_service.get_admin_user = AsyncMock(return_value=existing_user)
        mock_db_service.update_admin_user = AsyncMock(return_value=True)

        # 権限をエディターに更新
        result = await permission_manager.update_permission(
            user_id="U_EXISTING", new_permission=Permission.EDITOR
        )
        assert result is True

        # update_admin_userが呼ばれたことを確認
        mock_db_service.update_admin_user.assert_called_once()
        call_args = mock_db_service.update_admin_user.call_args[0][0]
        assert call_args.user_id == "U_EXISTING"
        assert call_args.permission == Permission.EDITOR

    @pytest.mark.asyncio
    async def test_update_permission_user_not_found(
        self, permission_manager, mock_db_service
    ):
        """存在しないユーザーの権限更新テスト"""
        mock_db_service.get_admin_user = AsyncMock(return_value=None)

        # ユーザーが存在しない場合はFalseを返す
        result = await permission_manager.update_permission(
            user_id="U_NOT_EXIST", new_permission=Permission.EDITOR
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_admin_user(self, permission_manager, mock_db_service):
        """管理者ユーザー削除のテスト"""
        mock_db_service.delete_admin_user = AsyncMock(return_value=True)

        result = await permission_manager.remove_admin_user("U_TO_DELETE")
        assert result is True

        # delete_admin_userが呼ばれたことを確認
        mock_db_service.delete_admin_user.assert_called_once_with("U_TO_DELETE")

    @pytest.mark.asyncio
    async def test_list_admin_users(self, permission_manager, mock_db_service):
        """管理者ユーザー一覧取得のテスト"""
        # モックデータ
        users = [
            AdminUser(
                user_id="U1",
                username="user1",
                permission=Permission.ADMIN,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            AdminUser(
                user_id="U2",
                username="user2",
                permission=Permission.EDITOR,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]
        mock_db_service.list_admin_users = AsyncMock(return_value=users)

        result = await permission_manager.list_admin_users()
        assert len(result) == 2
        assert result[0].user_id == "U1"
        assert result[0].permission == Permission.ADMIN
        assert result[1].user_id == "U2"
        assert result[1].permission == Permission.EDITOR

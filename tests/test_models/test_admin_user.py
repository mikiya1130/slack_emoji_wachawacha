"""
AdminUserモデルのテスト

権限管理機能のテストを実装
"""

import pytest
from datetime import datetime, UTC
from app.models.admin_user import AdminUser, Permission


class TestAdminUser:
    """AdminUserモデルのテストクラス"""

    def test_create_admin_user(self):
        """AdminUserの作成テスト"""
        user = AdminUser(
            user_id="U1234567890",
            username="test_user",
            permission=Permission.VIEWER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert user.user_id == "U1234567890"
        assert user.username == "test_user"
        assert user.permission == Permission.VIEWER
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_permission_enum(self):
        """Permission列挙型のテスト"""
        assert Permission.VIEWER.value == "viewer"
        assert Permission.EDITOR.value == "editor"
        assert Permission.ADMIN.value == "admin"

        # 権限レベルの比較
        assert Permission.ADMIN > Permission.EDITOR
        assert Permission.EDITOR > Permission.VIEWER

    def test_admin_user_validation(self):
        """AdminUserのバリデーションテスト"""
        # user_idが空の場合
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            AdminUser(user_id="", username="test_user", permission=Permission.VIEWER)

        # usernameが空の場合
        with pytest.raises(ValueError, match="username cannot be empty"):
            AdminUser(user_id="U1234567890", username="", permission=Permission.VIEWER)

    def test_to_dict(self):
        """辞書変換のテスト"""
        now = datetime.now(UTC)
        user = AdminUser(
            user_id="U1234567890",
            username="test_user",
            permission=Permission.EDITOR,
            created_at=now,
            updated_at=now,
        )

        user_dict = user.to_dict()
        assert user_dict["user_id"] == "U1234567890"
        assert user_dict["username"] == "test_user"
        assert user_dict["permission"] == "editor"
        assert user_dict["created_at"] == now.isoformat()
        assert user_dict["updated_at"] == now.isoformat()

    def test_from_dict(self):
        """辞書からの変換テスト"""
        now = datetime.now(UTC)
        user_dict = {
            "user_id": "U1234567890",
            "username": "test_user",
            "permission": "admin",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        user = AdminUser.from_dict(user_dict)
        assert user.user_id == "U1234567890"
        assert user.username == "test_user"
        assert user.permission == Permission.ADMIN
        assert user.created_at == now
        assert user.updated_at == now

    def test_has_permission(self):
        """権限チェックメソッドのテスト"""
        viewer = AdminUser(
            user_id="U1", username="viewer", permission=Permission.VIEWER
        )
        editor = AdminUser(
            user_id="U2", username="editor", permission=Permission.EDITOR
        )
        admin = AdminUser(user_id="U3", username="admin", permission=Permission.ADMIN)

        # Viewerの権限チェック
        assert viewer.has_permission(Permission.VIEWER) is True
        assert viewer.has_permission(Permission.EDITOR) is False
        assert viewer.has_permission(Permission.ADMIN) is False

        # Editorの権限チェック
        assert editor.has_permission(Permission.VIEWER) is True
        assert editor.has_permission(Permission.EDITOR) is True
        assert editor.has_permission(Permission.ADMIN) is False

        # Adminの権限チェック
        assert admin.has_permission(Permission.VIEWER) is True
        assert admin.has_permission(Permission.EDITOR) is True
        assert admin.has_permission(Permission.ADMIN) is True

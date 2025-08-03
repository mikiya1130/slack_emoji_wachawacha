"""
権限管理ユーティリティ

スラッシュコマンドでの権限チェック機能を提供
"""

import logging
from typing import List, TYPE_CHECKING

from app.models.admin_user import AdminUser, Permission

if TYPE_CHECKING:
    from app.services.database_service import DatabaseService


logger = logging.getLogger(__name__)


class PermissionManager:
    """権限管理クラス"""

    def __init__(self, db_service: "DatabaseService"):
        """初期化

        Args:
            db_service: データベースサービスインスタンス
        """
        self.db_service = db_service

    async def check_permission(
        self, user_id: str, required_permission: Permission
    ) -> bool:
        """ユーザーが必要な権限を持っているかチェック

        Args:
            user_id: SlackユーザーID
            required_permission: 必要な権限レベル

        Returns:
            bool: 権限を持っている場合True
        """
        try:
            # ユーザー情報を取得
            user = await self.db_service.get_admin_user(user_id)

            if user is None:
                # ユーザーが登録されていない場合、デフォルトでVIEWER権限
                default_permission = Permission.VIEWER
                logger.info(
                    f"User {user_id} not found in admin_users, "
                    f"using default permission: {default_permission.value}"
                )
                return default_permission >= required_permission

            # 権限チェック
            has_permission = user.has_permission(required_permission)
            logger.info(
                f"Permission check for user {user_id}: "
                f"required={required_permission.value}, "
                f"actual={user.permission.value}, "
                f"result={has_permission}"
            )
            return has_permission

        except Exception as e:
            logger.error(f"Error checking permission for user {user_id}: {e}")
            return False

    async def add_admin_user(
        self, user_id: str, username: str, permission: Permission
    ) -> bool:
        """管理者ユーザーを追加

        Args:
            user_id: SlackユーザーID
            username: ユーザー名
            permission: 権限レベル

        Returns:
            bool: 追加に成功した場合True
        """
        try:
            user = AdminUser(user_id=user_id, username=username, permission=permission)
            result = await self.db_service.save_admin_user(user)
            if result:
                logger.info(
                    f"Added admin user: {user_id} ({username}) "
                    f"with permission: {permission.value}"
                )
            return result
        except Exception as e:
            logger.error(f"Error adding admin user {user_id}: {e}")
            return False

    async def update_permission(self, user_id: str, new_permission: Permission) -> bool:
        """ユーザーの権限を更新

        Args:
            user_id: SlackユーザーID
            new_permission: 新しい権限レベル

        Returns:
            bool: 更新に成功した場合True
        """
        try:
            # 既存ユーザーを取得
            user = await self.db_service.get_admin_user(user_id)
            if user is None:
                logger.warning(f"User {user_id} not found for permission update")
                return False

            # 権限を更新
            user.permission = new_permission
            result = await self.db_service.update_admin_user(user)
            if result:
                logger.info(
                    f"Updated permission for user {user_id}: {new_permission.value}"
                )
            return result
        except Exception as e:
            logger.error(f"Error updating permission for user {user_id}: {e}")
            return False

    async def remove_admin_user(self, user_id: str) -> bool:
        """管理者ユーザーを削除

        Args:
            user_id: SlackユーザーID

        Returns:
            bool: 削除に成功した場合True
        """
        try:
            result = await self.db_service.delete_admin_user(user_id)
            if result:
                logger.info(f"Removed admin user: {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error removing admin user {user_id}: {e}")
            return False

    async def list_admin_users(self) -> List[AdminUser]:
        """管理者ユーザー一覧を取得

        Returns:
            List[AdminUser]: 管理者ユーザーのリスト
        """
        try:
            users = await self.db_service.list_admin_users()
            logger.info(f"Retrieved {len(users)} admin users")
            return users
        except Exception as e:
            logger.error(f"Error listing admin users: {e}")
            return []

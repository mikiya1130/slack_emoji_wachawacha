"""
管理者ユーザーモデル

スラッシュコマンドの権限管理用のデータモデル
"""

from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import Optional


class Permission(Enum):
    """権限レベル"""

    VIEWER = "viewer"  # 閲覧のみ（デフォルト）
    EDITOR = "editor"  # 編集可能
    ADMIN = "admin"  # 管理者権限

    def __lt__(self, other):
        """権限レベルの比較"""
        if not isinstance(other, Permission):
            return NotImplemented
        order = [Permission.VIEWER, Permission.EDITOR, Permission.ADMIN]
        return order.index(self) < order.index(other)

    def __le__(self, other):
        """権限レベルの比較"""
        return self == other or self < other

    def __gt__(self, other):
        """権限レベルの比較"""
        if not isinstance(other, Permission):
            return NotImplemented
        order = [Permission.VIEWER, Permission.EDITOR, Permission.ADMIN]
        return order.index(self) > order.index(other)

    def __ge__(self, other):
        """権限レベルの比較"""
        return self == other or self > other


@dataclass
class AdminUser:
    """管理者ユーザーモデル"""

    user_id: str
    username: str
    permission: Permission
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """初期化後の処理"""
        # バリデーション
        if not self.user_id:
            raise ValueError("user_id cannot be empty")
        if not self.username:
            raise ValueError("username cannot be empty")

        # タイムスタンプの設定
        now = datetime.now(UTC)
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    def to_dict(self) -> dict:
        """辞書への変換"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "permission": self.permission.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AdminUser":
        """辞書からのインスタンス生成"""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            permission=Permission(data["permission"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def has_permission(self, required_permission: Permission) -> bool:
        """必要な権限を持っているかチェック

        Args:
            required_permission: 必要な権限レベル

        Returns:
            bool: 権限を持っている場合True
        """
        return self.permission >= required_permission

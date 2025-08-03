# -*- coding: utf-8 -*-
"""Models module."""
from app.models.emoji import EmojiData
from app.models.admin_user import AdminUser, Permission

__all__ = ["EmojiData", "AdminUser", "Permission"]

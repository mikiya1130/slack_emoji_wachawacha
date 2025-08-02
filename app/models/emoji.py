"""
EmojiData - 絵文字データモデル

PostgreSQL emojisテーブルに対応するデータモデル:
- id: SERIAL PRIMARY KEY
- code: VARCHAR(100) NOT NULL UNIQUE (e.g., ":smile:")
- description: TEXT NOT NULL (semantic description)
- category: VARCHAR(50) (emoji category)
- emotion_tone: VARCHAR(20) (positive/negative/neutral)
- usage_scene: VARCHAR(100) (usage context)
- priority: INTEGER DEFAULT 1 (weighting factor)
- embedding: VECTOR(1536) (OpenAI embedding vector)
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any


class EmojiData:
    """
    絵文字データを表現するモデルクラス

    データベーステーブル 'emojis' に対応し、絵文字の
    メタデータと埋め込みベクトルを管理します。
    """

    # クラス定数
    VALID_EMOTION_TONES = {"positive", "negative", "neutral"}
    MAX_CODE_LENGTH = 100
    EMBEDDING_DIMENSION = 1536
    MIN_PRIORITY = 1
    MAX_PRIORITY = 10

    def __init__(
        self,
        code: str,
        description: str,
        category: Optional[str] = None,
        emotion_tone: Optional[str] = None,
        usage_scene: Optional[str] = None,
        priority: int = 1,
        id: Optional[int] = None,
        embedding: Optional[List[float]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        """
        EmojiDataインスタンスを初期化

        Args:
            code: 絵文字コード（例: ":smile:"）
            description: 絵文字の説明
            category: カテゴリ（任意）
            emotion_tone: 感情トーン（positive/negative/neutral）
            usage_scene: 使用シーン
            priority: 優先度（1-10）
            id: データベースID（任意）
            embedding: 埋め込みベクトル（1536次元）
            created_at: 作成日時
            updated_at: 更新日時

        Raises:
            ValueError: バリデーションエラー時
        """
        # 必須フィールドの検証と設定
        self.code = self._validate_and_set_code(code)
        self.description = self._validate_and_set_description(description)

        # オプションフィールドの検証と設定
        self.category = category
        self.emotion_tone = self._validate_and_set_emotion_tone(emotion_tone)
        self.usage_scene = usage_scene
        self.priority = self._validate_and_set_priority(priority)

        # システムフィールド
        self.id = id
        self.embedding = self._validate_and_set_embedding(embedding)
        self.created_at = created_at
        self.updated_at = updated_at

    def _validate_and_set_code(self, code: str) -> str:
        """絵文字コードのバリデーションと設定"""
        if not code:
            raise ValueError("code is required")

        if not isinstance(code, str):
            raise ValueError("code must be a string")

        # 絵文字コードの形式チェック（:で囲まれている）
        if not re.match(r"^:[^:]+:$", code):
            raise ValueError("Invalid emoji code format: must be like ':emoji_name:'")

        # 長さチェック（Slack制限）
        if len(code) > self.MAX_CODE_LENGTH:
            raise ValueError(f"code too long: {len(code)} > {self.MAX_CODE_LENGTH}")

        return code

    def _validate_and_set_description(self, description: str) -> str:
        """説明文のバリデーションと設定"""
        if not description:
            raise ValueError("description is required")

        if not isinstance(description, str):
            raise ValueError("description must be a string")

        return description.strip()

    def _validate_and_set_emotion_tone(
        self, emotion_tone: Optional[str]
    ) -> Optional[str]:
        """感情トーンのバリデーションと設定"""
        if emotion_tone is None:
            return None

        if emotion_tone not in self.VALID_EMOTION_TONES:
            raise ValueError(
                f"Invalid emotion_tone: {emotion_tone}. "
                f"Must be one of {list(self.VALID_EMOTION_TONES)}"
            )

        return emotion_tone

    def _validate_and_set_priority(self, priority: int) -> int:
        """優先度のバリデーションと設定"""
        if not isinstance(priority, int):
            raise ValueError("Invalid priority: must be an integer")

        if priority < self.MIN_PRIORITY or priority > self.MAX_PRIORITY:
            raise ValueError(
                f"Invalid priority: {priority}. "
                f"Must be between {self.MIN_PRIORITY} and {self.MAX_PRIORITY}"
            )

        return priority

    def _validate_and_set_embedding(
        self, embedding: Optional[List[float]]
    ) -> Optional[List[float]]:
        """埋め込みベクトルのバリデーションと設定"""
        if embedding is None:
            return None

        if not isinstance(embedding, list):
            raise ValueError("embedding must be a list")

        if len(embedding) != self.EMBEDDING_DIMENSION:
            raise ValueError(
                f"Invalid embedding dimension: {len(embedding)}. "
                f"Must be {self.EMBEDDING_DIMENSION}"
            )

        # すべての要素が数値であることを確認
        try:
            return [float(x) for x in embedding]
        except (ValueError, TypeError):
            raise ValueError("embedding must contain only numeric values")

    def to_dict(self) -> Dict[str, Any]:
        """
        インスタンスを辞書形式に変換

        Returns:
            Dict[str, Any]: 辞書形式のデータ
        """
        return {
            "id": self.id,
            "code": self.code,
            "description": self.description,
            "category": self.category,
            "emotion_tone": self.emotion_tone,
            "usage_scene": self.usage_scene,
            "priority": self.priority,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmojiData":
        """
        辞書からEmojiDataインスタンスを作成

        Args:
            data: 辞書形式のデータ

        Returns:
            EmojiData: 作成されたインスタンス
        """
        return cls(
            id=data.get("id"),
            code=data["code"],
            description=data["description"],
            category=data.get("category"),
            emotion_tone=data.get("emotion_tone"),
            usage_scene=data.get("usage_scene"),
            priority=data.get("priority", 1),
            embedding=data.get("embedding"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def is_valid(self) -> bool:
        """
        データの妥当性をチェック

        Returns:
            bool: 妥当な場合True
        """
        try:
            # 必須フィールドのチェック
            if not self.code or not self.description:
                return False

            # 各フィールドの妥当性をチェック
            self._validate_and_set_code(self.code)
            self._validate_and_set_description(self.description)

            if self.emotion_tone is not None:
                self._validate_and_set_emotion_tone(self.emotion_tone)

            self._validate_and_set_priority(self.priority)

            if self.embedding is not None:
                self._validate_and_set_embedding(self.embedding)

            return True

        except ValueError:
            return False

    def __str__(self) -> str:
        """文字列表現"""
        return f"EmojiData({self.code}: {self.description})"

    def __repr__(self) -> str:
        """詳細な文字列表現"""
        return (
            f"EmojiData(id={self.id}, code='{self.code}', "
            f"description='{self.description[:30]}...', "
            f"category='{self.category}', emotion_tone='{self.emotion_tone}', "
            f"priority={self.priority})"
        )

    def __eq__(self, other) -> bool:
        """等価性比較"""
        if not isinstance(other, EmojiData):
            return False

        return (
            self.code == other.code
            and self.description == other.description
            and self.category == other.category
            and self.emotion_tone == other.emotion_tone
            and self.usage_scene == other.usage_scene
            and self.priority == other.priority
        )

    def __hash__(self) -> int:
        """ハッシュ値計算（辞書のキーとして使用可能）"""
        return hash(
            (
                self.code,
                self.description,
                self.category,
                self.emotion_tone,
                self.usage_scene,
                self.priority,
            )
        )

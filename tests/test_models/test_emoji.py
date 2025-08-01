"""
EmojiData モデル単体テスト - TDD RED Phase

このテストは実装前に書かれており、最初は失敗することが期待されます。
EmojiDataクラスの期待される動作を定義します。

データ構造（emojisテーブル仕様）:
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

import pytest
from datetime import datetime


class TestEmojiData:
    """EmojiDataクラスの基本機能テスト"""
    
    def test_emoji_data_basic_initialization(self):
        """EmojiDataの基本初期化テスト - このテストは失敗するはず（RED Phase）"""
        # This should fail initially (RED phase)
        from app.models.emoji import EmojiData
            
        emoji = EmojiData(
            code=":smile:",
            description="Happy facial expression",
            category="emotions",
            emotion_tone="positive",
            usage_scene="greeting",
            priority=1
        )
            
        # 基本属性が正しく設定されることを確認
        assert emoji.code == ":smile:"
        assert emoji.description == "Happy facial expression"
        assert emoji.category == "emotions"
        assert emoji.emotion_tone == "positive"
        assert emoji.usage_scene == "greeting"
        assert emoji.priority == 1
            
        # デフォルト値の確認
        assert emoji.id is None  # 新規作成時はNone
        assert emoji.embedding is None  # 初期化時はNone
        assert emoji.created_at is None  # データベース挿入時に設定
        assert emoji.updated_at is None  # データベース挿入時に設定
            
    def test_emoji_data_with_full_parameters(self):
        """完全なパラメータでのEmojiData初期化テスト"""
        from app.models.emoji import EmojiData
            
        test_embedding = [0.1] * 1536  # OpenAI embedding dimension
        test_created_at = datetime.now()
        test_updated_at = datetime.now()
            
        emoji = EmojiData(
            id=1,
            code=":thumbsup:",
            description="Thumbs up gesture",
            category="gestures",
            emotion_tone="positive",
            usage_scene="approval",
            priority=2,
            embedding=test_embedding,
            created_at=test_created_at,
            updated_at=test_updated_at
        )
            
        # すべての属性が正しく設定されることを確認
        assert emoji.id == 1
        assert emoji.code == ":thumbsup:"
        assert emoji.description == "Thumbs up gesture"
        assert emoji.category == "gestures"
        assert emoji.emotion_tone == "positive"
        assert emoji.usage_scene == "approval"
        assert emoji.priority == 2
        assert emoji.embedding == test_embedding
        assert emoji.created_at == test_created_at
        assert emoji.updated_at == test_updated_at
            
class TestEmojiDataValidation:
    """EmojiDataのデータバリデーションテスト"""
    
    def test_emoji_code_validation_required(self):
        """絵文字コードの必須チェック"""
        from app.models.emoji import EmojiData
            
        # 空のコードでエラーが発生することを確認
        with pytest.raises(ValueError, match="code is required"):
            EmojiData(
                code="",
                description="Test description"
            )
            
        # Noneのコードでエラーが発生することを確認
        with pytest.raises(ValueError, match="code is required"):
            EmojiData(
                code=None,
                description="Test description"
            )
                
    def test_emoji_code_format_validation(self):
        """絵文字コードの形式チェック"""
        from app.models.emoji import EmojiData
            
        # 正常な形式
        valid_codes = [":smile:", ":thumbsup:", ":heart:", ":fire:"]
        for code in valid_codes:
            emoji = EmojiData(code=code, description="Test")
            assert emoji.code == code
            
        # 異常な形式でエラーが発生することを確認
        invalid_codes = ["smile", ":smile", "smile:", "::smile::"]
        for invalid_code in invalid_codes:
            with pytest.raises(ValueError, match="Invalid emoji code format"):
                EmojiData(code=invalid_code, description="Test")
            
        # 空文字列は別のエラーメッセージ
        with pytest.raises(ValueError, match="code is required"):
            EmojiData(code="", description="Test")
                    
    def test_emoji_code_length_validation(self):
        """絵文字コードの長さチェック（Slack制限: 100文字）"""
        from app.models.emoji import EmojiData
            
        # 境界値テスト（99文字）
        long_but_valid_code = ":" + "a" * 97 + ":"  # 99文字
        emoji = EmojiData(code=long_but_valid_code, description="Test")
        assert emoji.code == long_but_valid_code
            
        # 制限を超えた長さでエラーが発生することを確認（101文字）
        too_long_code = ":" + "a" * 99 + ":"  # 101文字
        with pytest.raises(ValueError, match="code too long"):
            EmojiData(code=too_long_code, description="Test")
                
    def test_description_validation_required(self):
        """説明文の必須チェック"""
        from app.models.emoji import EmojiData
            
        # 空の説明文でエラーが発生することを確認
        with pytest.raises(ValueError, match="description is required"):
            EmojiData(
                code=":smile:",
                description=""
            )
            
        # Noneの説明文でエラーが発生することを確認
        with pytest.raises(ValueError, match="description is required"):
            EmojiData(
                code=":smile:",
                description=None
            )
                
    def test_emotion_tone_validation(self):
        """感情トーンの妥当性チェック"""
        from app.models.emoji import EmojiData
            
        # 有効な感情トーン
        valid_tones = ["positive", "negative", "neutral"]
        for tone in valid_tones:
            emoji = EmojiData(
                code=":test:",
                description="Test",
                emotion_tone=tone
            )
            assert emoji.emotion_tone == tone
            
        # 無効な感情トーンでエラーが発生することを確認
        invalid_tones = ["happy", "sad", "unknown", "123"]
        for invalid_tone in invalid_tones:
            with pytest.raises(ValueError, match="Invalid emotion_tone"):
                EmojiData(
                    code=":test:",
                    description="Test",
                    emotion_tone=invalid_tone
                )
                    
    def test_priority_validation(self):
        """優先度の妥当性チェック"""
        from app.models.emoji import EmojiData
            
        # 有効な優先度（1-10）
        valid_priorities = [1, 2, 5, 8, 10]
        for priority in valid_priorities:
            emoji = EmojiData(
                code=":test:",
                description="Test",
                priority=priority
            )
            assert emoji.priority == priority
            
        # 無効な優先度でエラーが発生することを確認
        invalid_priorities = [0, -1, 11, 100, "1", None]
        for invalid_priority in invalid_priorities:
            with pytest.raises(ValueError, match="Invalid priority"):
                EmojiData(
                    code=":test:",
                    description="Test",
                    priority=invalid_priority
                )
                    
    def test_embedding_validation(self):
        """埋め込みベクトルの妥当性チェック"""
        from app.models.emoji import EmojiData
            
        # 正しい次元数のベクトル（1536次元）
        valid_embedding = [0.1] * 1536
        emoji = EmojiData(
            code=":test:",
            description="Test",
            embedding=valid_embedding
        )
        assert emoji.embedding == valid_embedding
            
        # 間違った次元数でエラーが発生することを確認
        wrong_dimension_embeddings = [
            [0.1] * 100,   # 100次元
            [0.1] * 768,   # 768次元  
            [0.1] * 2048,  # 2048次元
            []             # 空のリスト
        ]
            
        for wrong_embedding in wrong_dimension_embeddings:
            with pytest.raises(ValueError, match="Invalid embedding dimension"):
                EmojiData(
                    code=":test:",
                    description="Test",
                    embedding=wrong_embedding
                )
                    
class TestEmojiDataMethods:
    """EmojiDataクラスのメソッドテスト"""
    
    def test_to_dict_method(self):
        """辞書形式への変換テスト"""
        from app.models.emoji import EmojiData
            
        emoji = EmojiData(
            id=1,
            code=":smile:",
            description="Happy expression",
            category="emotions",
            emotion_tone="positive", 
            usage_scene="greeting",
            priority=1
        )
            
        result = emoji.to_dict()
            
        expected = {
            "id": 1,
            "code": ":smile:",
            "description": "Happy expression",
            "category": "emotions",
            "emotion_tone": "positive",
            "usage_scene": "greeting",
            "priority": 1,
            "embedding": None,
            "created_at": None,
            "updated_at": None
        }
            
        assert result == expected
            
    def test_from_dict_class_method(self):
        """辞書からのインスタンス作成テスト"""
        from app.models.emoji import EmojiData
            
        data = {
            "id": 1,
            "code": ":thumbsup:",
            "description": "Approval gesture",
            "category": "gestures",
            "emotion_tone": "positive",
            "usage_scene": "approval",
            "priority": 2,
            "embedding": [0.1] * 1536,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
            
        emoji = EmojiData.from_dict(data)
            
        assert emoji.id == 1
        assert emoji.code == ":thumbsup:"
        assert emoji.description == "Approval gesture"
        assert emoji.category == "gestures"
        assert emoji.emotion_tone == "positive"
        assert emoji.usage_scene == "approval"
        assert emoji.priority == 2
        assert emoji.embedding == data["embedding"]
        assert emoji.created_at == data["created_at"]
        assert emoji.updated_at == data["updated_at"]
            
    def test_is_valid_method(self):
        """データ妥当性チェックメソッドテスト"""
        from app.models.emoji import EmojiData
            
        # 有効なデータ
        valid_emoji = EmojiData(
            code=":smile:",
            description="Happy expression"
        )
        assert valid_emoji.is_valid() is True
            
        # 無効なデータ（実装によって検証される）
        # このテストは実装でどのような検証が行われるかを定義する
            
    def test_str_and_repr_methods(self):
        """文字列表現メソッドテスト"""
        from app.models.emoji import EmojiData
            
        emoji = EmojiData(
            code=":smile:",
            description="Happy expression"
        )
            
        # __str__メソッドのテスト
        str_result = str(emoji)
        assert ":smile:" in str_result
        assert "Happy expression" in str_result
            
        # __repr__メソッドのテスト
        repr_result = repr(emoji)
        assert "EmojiData" in repr_result
        assert ":smile:" in repr_result
            
class TestEmojiDataComparison:
    """EmojiData比較機能テスト"""
    
    def test_equality_comparison(self):
        """等価性比較テスト"""
        from app.models.emoji import EmojiData
            
        emoji1 = EmojiData(
            code=":smile:",
            description="Happy expression"
        )
            
        emoji2 = EmojiData(
            code=":smile:",
            description="Happy expression"
        )
            
        emoji3 = EmojiData(
            code=":frown:",
            description="Sad expression"
        )
            
        # 同じ内容なら等価
        assert emoji1 == emoji2
            
        # 異なる内容なら非等価
        assert emoji1 != emoji3
            
    def test_hash_support(self):
        """ハッシュサポートテスト（辞書のキーとして使用可能）"""
        from app.models.emoji import EmojiData
            
        emoji1 = EmojiData(
            code=":smile:",
            description="Happy expression"
        )
            
        emoji2 = EmojiData(
            code=":frown:",
            description="Sad expression"
        )
            
        # 辞書のキーとして使用できることを確認
        emoji_dict = {
            emoji1: "happy",
            emoji2: "sad"
        }
            
        assert emoji_dict[emoji1] == "happy"
        assert emoji_dict[emoji2] == "sad"
            
@pytest.fixture
def sample_emoji_data():
    """テスト用のサンプル絵文字データ"""
    return {
        "id": 1,
        "code": ":test_emoji:",
        "description": "Test emoji for unit testing",
        "category": "test",
        "emotion_tone": "neutral",
        "usage_scene": "testing",
        "priority": 1,
        "embedding": [0.1] * 1536,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


class TestEmojiDataEdgeCases:
    """EmojiDataのエッジケーステスト"""
    
    def test_unicode_emoji_code_handling(self):
        """Unicode絵文字コードの処理テスト"""
        from app.models.emoji import EmojiData
            
        # Unicode文字を含む絵文字コード
        unicode_codes = [":café:", ":naïve:", ":résumé:"]
            
        for code in unicode_codes:
            emoji = EmojiData(
                code=code,
                description="Unicode test"
            )
            assert emoji.code == code
                
    def test_very_long_description_handling(self):
        """非常に長い説明文の処理テスト"""
        from app.models.emoji import EmojiData
            
        # 非常に長い説明文（1000文字）
        long_description = "A" * 1000
            
        emoji = EmojiData(
            code=":test:",
            description=long_description
        )
            
        assert emoji.description == long_description
            
    def test_special_characters_in_fields(self):
        """フィールド内の特殊文字処理テスト"""
        from app.models.emoji import EmojiData
            
        # 特殊文字を含むデータ
        emoji = EmojiData(
            code=":test:",
            description="Special chars: !@#$%^&*()[]{}|\\:;\"'<>?/.,`~",
            category="special-chars",
            usage_scene="testing&validation"
        )
            
        assert "!@#$%^&*" in emoji.description
        assert emoji.category == "special-chars"
        assert emoji.usage_scene == "testing&validation"
            
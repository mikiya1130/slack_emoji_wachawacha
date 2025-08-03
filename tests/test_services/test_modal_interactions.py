"""
モーダルインタラクションのテスト

Slackモーダルのフォーム送信とバリデーションのテスト
"""

import pytest

from app.services.modal_handler import ModalHandler, EmojiFormData
from app.models.emoji import EmojiData


class TestModalHandler:
    """ModalHandlerのテストクラス"""

    @pytest.fixture
    def modal_handler(self):
        """ModalHandlerインスタンス"""
        return ModalHandler()

    def test_create_emoji_add_modal(self, modal_handler):
        """絵文字追加モーダルの作成テスト"""
        modal = modal_handler.create_emoji_add_modal()

        assert modal["type"] == "modal"
        assert modal["callback_id"] == "emoji_add_modal"
        assert modal["title"]["text"] == "Add New Emoji"
        assert modal["submit"]["text"] == "Add"
        assert modal["close"]["text"] == "Cancel"

        # ブロックの確認
        blocks = modal["blocks"]
        assert len(blocks) >= 6  # 最低6つの入力フィールド

        # 各ブロックのIDを確認
        block_ids = [block["block_id"] for block in blocks if "block_id" in block]
        assert "emoji_code" in block_ids
        assert "description" in block_ids
        assert "category" in block_ids
        assert "emotion_tone" in block_ids
        assert "usage_scene" in block_ids
        assert "priority" in block_ids

    def test_create_emoji_update_modal(self, modal_handler):
        """絵文字更新モーダルの作成テスト"""
        emoji_data = EmojiData(
            id=1,
            code=":custom:",
            description="Custom emoji",
            category="objects",
            emotion_tone="neutral",
            usage_scene="general",
            priority=1,
        )

        modal = modal_handler.create_emoji_update_modal(emoji_data)

        assert modal["type"] == "modal"
        assert modal["callback_id"] == "emoji_update_modal"
        assert modal["title"]["text"] == "Update Emoji"
        assert modal["submit"]["text"] == "Update"

        # 初期値が設定されていることを確認
        code_block = next(
            b for b in modal["blocks"] if b.get("block_id") == "emoji_code"
        )
        assert code_block["element"]["initial_value"] == ":custom:"

    def test_create_vectorization_confirm_modal(self, modal_handler):
        """ベクトル化確認モーダルの作成テスト"""
        emoji_count = 150

        modal = modal_handler.create_vectorization_confirm_modal(emoji_count)

        assert modal["type"] == "modal"
        assert modal["callback_id"] == "vectorize_confirm_modal"
        assert modal["title"]["text"] == "Confirm Vectorization"
        assert "150 emojis" in modal["blocks"][0]["text"]["text"]

        # アクションボタンの確認
        actions = modal["blocks"][-1]["elements"]
        assert len(actions) == 2
        assert actions[0]["action_id"] == "vectorize_confirm"
        assert actions[1]["action_id"] == "vectorize_cancel"

    def test_parse_emoji_form_submission(self, modal_handler):
        """絵文字フォーム送信データの解析テスト"""
        submission_values = {
            "emoji_code": {"emoji_code_input": {"value": ":test:"}},
            "description": {"description_input": {"value": "Test emoji"}},
            "category": {"category_select": {"selected_option": {"value": "objects"}}},
            "emotion_tone": {
                "emotion_select": {"selected_option": {"value": "positive"}}
            },
            "usage_scene": {"usage_input": {"value": "testing"}},
            "priority": {"priority_input": {"value": "5"}},
        }

        form_data = modal_handler.parse_emoji_form_submission(submission_values)

        assert isinstance(form_data, EmojiFormData)
        assert form_data.code == ":test:"
        assert form_data.description == "Test emoji"
        assert form_data.category == "objects"
        assert form_data.emotion_tone == "positive"
        assert form_data.usage_scene == "testing"
        assert form_data.priority == 5

    def test_validate_emoji_code(self, modal_handler):
        """絵文字コードのバリデーションテスト"""
        # 正常なコード
        assert modal_handler.validate_emoji_code(":test:") is True
        assert modal_handler.validate_emoji_code(":test_emoji:") is True
        assert modal_handler.validate_emoji_code(":test-emoji:") is True
        assert modal_handler.validate_emoji_code(":test123:") is True

        # 異常なコード
        assert modal_handler.validate_emoji_code("test") is False
        assert modal_handler.validate_emoji_code(":test") is False
        assert modal_handler.validate_emoji_code("test:") is False
        assert modal_handler.validate_emoji_code("::test::") is False
        assert modal_handler.validate_emoji_code(":te st:") is False
        assert modal_handler.validate_emoji_code("") is False

    def test_validate_form_data(self, modal_handler):
        """フォームデータのバリデーションテスト"""
        # 正常なデータ
        valid_data = EmojiFormData(
            code=":test:",
            description="Test emoji",
            category="objects",
            emotion_tone="positive",
            usage_scene="testing",
            priority=1,
        )
        errors = modal_handler.validate_form_data(valid_data)
        assert len(errors) == 0

        # コードが不正
        invalid_code_data = EmojiFormData(
            code="invalid",
            description="Test",
            category="objects",
            emotion_tone="positive",
            usage_scene="testing",
            priority=1,
        )
        errors = modal_handler.validate_form_data(invalid_code_data)
        assert len(errors) > 0
        assert any("code" in error for error in errors)

        # 説明が空
        empty_desc_data = EmojiFormData(
            code=":test:",
            description="",
            category="objects",
            emotion_tone="positive",
            usage_scene="testing",
            priority=1,
        )
        errors = modal_handler.validate_form_data(empty_desc_data)
        assert len(errors) > 0
        assert any("description" in error for error in errors)

        # 優先度が範囲外
        invalid_priority_data = EmojiFormData(
            code=":test:",
            description="Test",
            category="objects",
            emotion_tone="positive",
            usage_scene="testing",
            priority=11,
        )
        errors = modal_handler.validate_form_data(invalid_priority_data)
        assert len(errors) > 0
        assert any("priority" in error for error in errors)

    def test_create_error_response(self, modal_handler):
        """エラーレスポンスの作成テスト"""
        errors = ["Invalid emoji code format", "Description cannot be empty"]

        response = modal_handler.create_error_response(errors)

        assert response["response_type"] == "ephemeral"
        assert response["text"] == "There were errors with your submission:"
        assert len(response["blocks"]) == 2
        assert response["blocks"][0]["type"] == "section"
        assert "Invalid emoji code format" in response["blocks"][1]["text"]["text"]
        assert "Description cannot be empty" in response["blocks"][1]["text"]["text"]

    def test_create_success_response(self, modal_handler):
        """成功レスポンスの作成テスト"""
        emoji_code = ":success:"
        action = "added"

        response = modal_handler.create_success_response(emoji_code, action)

        assert response["response_type"] == "ephemeral"
        assert response["text"] == f"Emoji {emoji_code} {action} successfully!"
        assert response["blocks"][0]["type"] == "section"
        assert (
            f"✅ Emoji `{emoji_code}` has been {action} successfully!"
            in response["blocks"][0]["text"]["text"]
        )

    def test_create_emoji_list_blocks(self, modal_handler):
        """絵文字リストブロックの作成テスト"""
        emojis = [
            EmojiData(code=":smile:", description="Smiling face", category="emotions"),
            EmojiData(code=":thumbsup:", description="Thumbs up", category="gestures"),
            EmojiData(code=":book:", description="Book", category="objects"),
        ]

        blocks = modal_handler.create_emoji_list_blocks(emojis)

        assert len(blocks) >= 2  # ヘッダー + 絵文字セクション
        assert blocks[0]["type"] == "header"
        assert "Emoji List" in blocks[0]["text"]["text"]

        # 絵文字が含まれていることを確認
        emoji_texts = []
        for block in blocks[1:]:
            if block["type"] == "section" and "fields" in block:
                emoji_texts.extend([field["text"] for field in block["fields"]])

        assert any(":smile:" in text for text in emoji_texts)
        assert any(":thumbsup:" in text for text in emoji_texts)
        assert any(":book:" in text for text in emoji_texts)

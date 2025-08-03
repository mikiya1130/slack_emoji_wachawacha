"""
モーダルハンドラー

Slackモーダルのフォーム処理とバリデーション
"""

import re
from dataclasses import dataclass
from typing import Dict, Any, List

from app.models.emoji import EmojiData


@dataclass
class EmojiFormData:
    """絵文字フォームデータ"""

    code: str
    description: str
    category: str
    emotion_tone: str
    usage_scene: str
    priority: int


class ModalHandler:
    """モーダルハンドラークラス"""

    def create_emoji_add_modal(self) -> Dict[str, Any]:
        """絵文字追加モーダルを作成"""
        return {
            "type": "modal",
            "callback_id": "emoji_add_modal",
            "title": {"type": "plain_text", "text": "Add New Emoji"},
            "submit": {"type": "plain_text", "text": "Add"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "emoji_code",
                    "label": {"type": "plain_text", "text": "Emoji Code"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "emoji_code_input",
                        "placeholder": {"type": "plain_text", "text": ":example:"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "description",
                    "label": {"type": "plain_text", "text": "Description"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "description_input",
                        "multiline": True,
                    },
                },
                {
                    "type": "input",
                    "block_id": "category",
                    "label": {"type": "plain_text", "text": "Category"},
                    "element": {
                        "type": "static_select",
                        "action_id": "category_select",
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Emotions"},
                                "value": "emotions",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Gestures"},
                                "value": "gestures",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Objects"},
                                "value": "objects",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Symbols"},
                                "value": "symbols",
                            },
                        ],
                    },
                },
                {
                    "type": "input",
                    "block_id": "emotion_tone",
                    "label": {"type": "plain_text", "text": "Emotion Tone"},
                    "element": {
                        "type": "static_select",
                        "action_id": "emotion_select",
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Positive"},
                                "value": "positive",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Negative"},
                                "value": "negative",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Neutral"},
                                "value": "neutral",
                            },
                        ],
                    },
                },
                {
                    "type": "input",
                    "block_id": "usage_scene",
                    "label": {"type": "plain_text", "text": "Usage Scene"},
                    "element": {"type": "plain_text_input", "action_id": "usage_input"},
                },
                {
                    "type": "input",
                    "block_id": "priority",
                    "label": {"type": "plain_text", "text": "Priority (1-10)"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "priority_input",
                        "initial_value": "1",
                    },
                },
            ],
        }

    def create_emoji_update_modal(self, emoji_data: EmojiData) -> Dict[str, Any]:
        """絵文字更新モーダルを作成"""
        return {
            "type": "modal",
            "callback_id": "emoji_update_modal",
            "title": {"type": "plain_text", "text": "Update Emoji"},
            "submit": {"type": "plain_text", "text": "Update"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "emoji_code",
                    "label": {"type": "plain_text", "text": "Emoji Code"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "emoji_code_input",
                        "initial_value": emoji_data.code,
                    },
                },
                {
                    "type": "input",
                    "block_id": "description",
                    "label": {"type": "plain_text", "text": "Description"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "description_input",
                        "multiline": True,
                        "initial_value": emoji_data.description,
                    },
                },
                {
                    "type": "input",
                    "block_id": "category",
                    "label": {"type": "plain_text", "text": "Category"},
                    "element": {
                        "type": "static_select",
                        "action_id": "category_select",
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": (
                                    emoji_data.category.title()
                                    if emoji_data.category
                                    else ""
                                ),
                            },
                            "value": emoji_data.category,
                        },
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Emotions"},
                                "value": "emotions",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Gestures"},
                                "value": "gestures",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Objects"},
                                "value": "objects",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Symbols"},
                                "value": "symbols",
                            },
                        ],
                    },
                },
                {
                    "type": "input",
                    "block_id": "emotion_tone",
                    "label": {"type": "plain_text", "text": "Emotion Tone"},
                    "element": {
                        "type": "static_select",
                        "action_id": "emotion_select",
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": (
                                    emoji_data.emotion_tone.title()
                                    if emoji_data.emotion_tone
                                    else ""
                                ),
                            },
                            "value": emoji_data.emotion_tone,
                        },
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "Positive"},
                                "value": "positive",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Negative"},
                                "value": "negative",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Neutral"},
                                "value": "neutral",
                            },
                        ],
                    },
                },
                {
                    "type": "input",
                    "block_id": "usage_scene",
                    "label": {"type": "plain_text", "text": "Usage Scene"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "usage_input",
                        "initial_value": emoji_data.usage_scene,
                    },
                },
                {
                    "type": "input",
                    "block_id": "priority",
                    "label": {"type": "plain_text", "text": "Priority (1-10)"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "priority_input",
                        "initial_value": str(emoji_data.priority),
                    },
                },
            ],
        }

    def create_vectorization_confirm_modal(self, emoji_count: int) -> Dict[str, Any]:
        """ベクトル化確認モーダルを作成"""
        return {
            "type": "modal",
            "callback_id": "vectorize_confirm_modal",
            "title": {"type": "plain_text", "text": "Confirm Vectorization"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"This will vectorize {emoji_count} emojis. "
                            "This operation may take several minutes."
                        ),
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Confirm"},
                            "style": "primary",
                            "action_id": "vectorize_confirm",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Cancel"},
                            "action_id": "vectorize_cancel",
                        },
                    ],
                },
            ],
        }

    def parse_emoji_form_submission(
        self, submission_values: Dict[str, Any]
    ) -> EmojiFormData:
        """絵文字フォーム送信データを解析"""
        return EmojiFormData(
            code=submission_values["emoji_code"]["emoji_code_input"]["value"],
            description=submission_values["description"]["description_input"]["value"],
            category=submission_values["category"]["category_select"][
                "selected_option"
            ]["value"],
            emotion_tone=submission_values["emotion_tone"]["emotion_select"][
                "selected_option"
            ]["value"],
            usage_scene=submission_values["usage_scene"]["usage_input"]["value"],
            priority=int(submission_values["priority"]["priority_input"]["value"]),
        )

    def validate_emoji_code(self, code: str) -> bool:
        """絵文字コードのバリデーション"""
        # :text: 形式であることを確認
        pattern = r"^:[a-zA-Z0-9_\-]+:$"
        return bool(re.match(pattern, code))

    def validate_form_data(self, form_data: EmojiFormData) -> List[str]:
        """フォームデータのバリデーション"""
        errors = []

        # 絵文字コードのバリデーション
        if not self.validate_emoji_code(form_data.code):
            errors.append("Invalid emoji code format. Must be in :code: format.")

        # 説明のバリデーション
        if not form_data.description or form_data.description.strip() == "":
            errors.append("Invalid description: cannot be empty.")

        # 優先度のバリデーション
        if form_data.priority < 1 or form_data.priority > 10:
            errors.append("Invalid priority: must be between 1 and 10.")

        return errors

    def create_error_response(self, errors: List[str]) -> Dict[str, Any]:
        """エラーレスポンスを作成"""
        error_text = "\n".join([f"• {error}" for error in errors])

        return {
            "response_type": "ephemeral",
            "text": "There were errors with your submission:",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "There were errors with your submission:",
                    },
                },
                {"type": "section", "text": {"type": "mrkdwn", "text": error_text}},
            ],
        }

    def create_success_response(self, emoji_code: str, action: str) -> Dict[str, Any]:
        """成功レスポンスを作成"""
        return {
            "response_type": "ephemeral",
            "text": f"Emoji {emoji_code} {action} successfully!",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ Emoji `{emoji_code}` has been {action} successfully!",
                    },
                }
            ],
        }

    def create_emoji_list_blocks(self, emojis: List[EmojiData]) -> List[Dict[str, Any]]:
        """絵文字リストブロックを作成"""
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "Emoji List"}}
        ]

        # 絵文字をグループ化してセクションに追加
        emoji_fields: List[Dict[str, Any]] = []
        for emoji in emojis:
            emoji_fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"{emoji.code}\n{emoji.description}\n_{emoji.category}_",
                }
            )

            # 10個ごとにセクションを作成
            if len(emoji_fields) == 10:
                blocks.append({"type": "section", "fields": emoji_fields})  # type: ignore
                emoji_fields = []

        # 残りのフィールドがあれば追加
        if emoji_fields:
            blocks.append({"type": "section", "fields": emoji_fields})  # type: ignore

        return blocks

    def create_vectorization_progress_blocks(
        self, progress: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """ベクトル化進捗表示ブロックを作成"""
        current = progress.get("current", 0)
        total = progress.get("total", 0)
        percentage = progress.get("percentage", 0)
        emoji_code = progress.get("emoji_code", "")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🔄 Vectorization Progress"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Progress: *{percentage}%* ({current}/{total})",
                },
            },
        ]

        if emoji_code:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Currently processing: `{emoji_code}`",
                    },
                }
            )

        # プログレスバー
        bar_length = 20
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"`{bar}` {percentage}%"},
            }
        )

        return blocks

    def create_vectorization_result_blocks(
        self, result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """ベクトル化結果表示ブロックを作成"""
        processed = result.get("processed", 0)
        skipped = result.get("skipped", 0)
        filtered_out = result.get("filtered_out", 0)
        total = result.get("total", 0)
        duration = result.get("duration", 0)

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅ Vectorization Complete"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Emojis:*\n{total}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Processed:*\n{processed}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Skipped:*\n{skipped}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Filtered Out:*\n{filtered_out}",
                    },
                ],
            },
        ]

        if duration:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⏱️ Duration: *{duration:.1f} seconds*",
                    },
                }
            )

        # 成功率
        if total > 0:
            success_rate = (processed / total) * 100
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📊 Success Rate: *{success_rate:.1f}%*",
                    },
                }
            )

        return blocks  # type: ignore

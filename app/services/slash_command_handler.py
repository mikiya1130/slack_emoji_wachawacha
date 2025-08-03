"""
スラッシュコマンドハンドラー

/emojiコマンドのルーティングと処理を管理
"""

import asyncio
import logging
from typing import Dict, Any, List, Tuple

from app.models.admin_user import Permission
from app.utils.permission_manager import PermissionManager
from app.services.emoji_service import EmojiService
from app.services.slack_handler import SlackHandler
from app.services.modal_handler import ModalHandler

logger = logging.getLogger(__name__)


class SlashCommandHandler:
    """スラッシュコマンドハンドラークラス"""

    def __init__(
        self,
        slack_handler: SlackHandler,
        emoji_service: EmojiService,
        permission_manager: PermissionManager,
    ):
        """初期化

        Args:
            slack_handler: Slackハンドラーインスタンス
            emoji_service: 絵文字サービスインスタンス
            permission_manager: 権限管理インスタンス
        """
        self.slack_handler = slack_handler
        self.emoji_service = emoji_service
        self.permission_manager = permission_manager
        self.modal_handler = ModalHandler()

    async def handle_emoji_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        /emojiコマンドを処理

        Args:
            payload: Slackからのコマンドペイロード

        Returns:
            Dict[str, Any]: レスポンス
        """
        user_id = payload["user_id"]
        command_text = payload.get("text", "").strip()

        # コマンドテキストを解析
        subcommand, args = self.parse_command_text(command_text)

        try:
            # サブコマンドに応じて処理
            if subcommand == "help":
                return self._create_help_response()

            elif subcommand == "list":
                # VIEWER権限が必要
                if not await self.permission_manager.check_permission(
                    user_id, Permission.VIEWER
                ):
                    return self._create_permission_denied_response(Permission.VIEWER)

                emojis = await self.emoji_service.get_all_emojis()
                return self._create_list_response(emojis)

            elif subcommand == "add":
                # EDITOR権限が必要
                if not await self.permission_manager.check_permission(
                    user_id, Permission.EDITOR
                ):
                    return self._create_permission_denied_response(Permission.EDITOR)

                # モーダルを開く
                await self.slack_handler.open_modal(
                    trigger_id=payload["trigger_id"],
                    modal=self._create_add_emoji_modal(),
                )
                return {
                    "response_type": "ephemeral",
                    "text": "Opening emoji add form...",
                }

            elif subcommand == "search":
                if not args:
                    return {
                        "response_type": "ephemeral",
                        "text": "Please provide a search term: `/emoji search <term>`",
                    }

                search_term = " ".join(args)
                emojis = await self.emoji_service.search_emojis(search_term)
                return self._create_search_response(search_term, emojis)

            elif subcommand == "delete":
                # EDITOR権限が必要
                if not await self.permission_manager.check_permission(
                    user_id, Permission.EDITOR
                ):
                    return self._create_permission_denied_response(Permission.EDITOR)

                if not args:
                    return {
                        "response_type": "ephemeral",
                        "text": "Please provide an emoji code: `/emoji delete <emoji_code>`",
                    }

                emoji_code = args[0]
                success = await self.emoji_service.delete_emoji_by_code(emoji_code)

                if success:
                    return {
                        "response_type": "ephemeral",
                        "text": f"Emoji {emoji_code} deleted successfully",
                    }
                else:
                    return {
                        "response_type": "ephemeral",
                        "text": f"Failed to delete emoji {emoji_code}",
                    }

            elif subcommand == "vectorize":
                # ADMIN権限が必要
                if not await self.permission_manager.check_permission(
                    user_id, Permission.ADMIN
                ):
                    return self._create_permission_denied_response(Permission.ADMIN)

                # オプションの解析（後でモーダルに渡すために保持）
                self.parse_vectorize_options(args)

                # 絵文字数を取得
                emoji_count = await self.emoji_service.count_emojis()

                # 確認モーダルを開く
                trigger_id = payload.get("trigger_id")
                if trigger_id:
                    modal = self.modal_handler.create_vectorization_confirm_modal(
                        emoji_count
                    )
                    await self.slack_handler.open_modal(trigger_id, modal)

                    if "--dry-run" in args:
                        return {
                            "response_type": "ephemeral",
                            "text": "Opening vectorization confirmation... (dry run mode)",
                        }
                    elif "--skip-existing" in args:
                        return {
                            "response_type": "ephemeral",
                            "text": "Opening vectorization confirmation... (skip existing mode)",
                        }
                    else:
                        return {
                            "response_type": "ephemeral",
                            "text": "Opening vectorization confirmation...",
                        }
                else:
                    return self._create_error_response("Trigger ID not provided")

            elif subcommand == "stats":
                stats = await self.emoji_service.get_emoji_stats()
                return self._create_stats_response(stats)

            else:
                return {
                    "response_type": "ephemeral",
                    "text": (
                        f"Unknown command: {subcommand}. "
                        "Use '/emoji help' for available commands."
                    ),
                }

        except Exception as e:
            logger.error(f"Error handling emoji command: {e}")
            return {
                "response_type": "ephemeral",
                "text": (
                    "An error occurred while processing your command. "
                    "Please try again later."
                ),
            }

    def parse_command_text(self, text: str) -> Tuple[str, List[str]]:
        """
        コマンドテキストを解析

        Args:
            text: コマンドテキスト

        Returns:
            Tuple[str, List[str]]: (サブコマンド, 引数リスト)
        """
        if not text:
            return "help", []

        parts = text.split()
        subcommand = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        return subcommand, args

    def parse_vectorize_options(self, args: List[str]) -> Dict[str, Any]:
        """
        ベクトル化コマンドのオプションを解析

        Args:
            args: コマンド引数リスト

        Returns:
            Dict[str, Any]: オプション辞書
        """
        options = {
            "skip_existing": "--skip-existing" in args,
            "dry_run": "--dry-run" in args,
        }
        return options

    async def handle_emoji_add_submission(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        絵文字追加モーダルの送信を処理

        Args:
            payload: モーダル送信ペイロード

        Returns:
            Dict[str, Any]: レスポンス
        """
        values = payload["view"]["state"]["values"]

        # フォームデータを抽出
        emoji_data = {
            "code": values["emoji_code"]["emoji_code_input"]["value"],
            "description": values["description"]["description_input"]["value"],
            "category": values["category"]["category_select"]["selected_option"][
                "value"
            ],
            "emotion_tone": values["emotion_tone"]["emotion_select"]["selected_option"][
                "value"
            ],
            "usage_scene": values["usage_scene"]["usage_input"]["value"],
            "priority": int(values["priority"]["priority_input"]["value"]),
        }

        # 絵文字を作成
        await self.emoji_service.create_emoji(emoji_data)

        return {
            "response_type": "ephemeral",
            "text": f"Emoji {emoji_data['code']} added successfully!",
        }

    async def handle_vectorization_action(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ベクトル化アクションを処理

        Args:
            payload: アクションペイロード

        Returns:
            Dict[str, Any]: レスポンス
        """
        action = payload["actions"][0]

        if action["action_id"] == "vectorize_confirm":
            # ベクトル化を実行
            result = await self.emoji_service.vectorize_all_emojis()

            return {
                "response_type": "ephemeral",
                "text": (
                    f"Vectorization started!\n"
                    f"Total: {result['total']}\n"
                    f"Success: {result['success']}\n"
                    f"Failed: {result['failed']}"
                ),
            }

        return {"response_type": "ephemeral", "text": "Vectorization cancelled."}

    async def handle_action(self, payload: Dict[str, Any]) -> None:
        """
        ボタンアクションを処理

        Args:
            payload: アクションペイロード
        """
        action = payload["actions"][0]
        action_id = action["action_id"]
        user_id = payload["user"]["id"]
        response_url = payload.get("response_url")

        if action_id == "vectorize_confirm":
            # 即座の応答
            await self.slack_handler.send_ephemeral_message(
                channel="",  # response_urlを使うので不要
                user=user_id,
                text="✅ Vectorization started! Processing in background...",
            )

            # バックグラウンドでベクトル化を実行
            options: Dict[str, Any] = {}  # TODO: モーダルから状態を取得
            if response_url:
                asyncio.create_task(
                    self._run_vectorization_task(user_id, response_url, options)
                )

        elif action_id == "vectorize_cancel":
            await self.slack_handler.send_ephemeral_message(
                channel="",
                user=user_id,
                text="❌ Vectorization cancelled.",
            )

    async def _run_vectorization_task(
        self, user_id: str, response_url: str, options: Dict[str, Any]
    ) -> None:
        """
        バックグラウンドでベクトル化タスクを実行

        Args:
            user_id: ユーザーID
            response_url: レスポンスURL
            options: ベクトル化オプション
        """
        try:
            # 開始メッセージ
            await self.slack_handler.post_message_with_blocks(
                channel=user_id,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "🔄 Vectorization in progress...",
                        },
                    }
                ],
                text="🔄 Vectorization in progress...",
            )

            # プログレスコールバック
            async def progress_callback(current: int, total: int, emoji_code: str):
                percentage = int((current / total) * 100)
                await self.slack_handler.post_message_with_blocks(
                    channel=user_id,
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"🔄 Progress: {percentage}% "
                                    f"({current}/{total}) - Processing {emoji_code}"
                                ),
                            },
                        }
                    ],
                    text=f"🔄 Progress: {percentage}% ({current}/{total}) - Processing {emoji_code}",
                )

            # ベクトル化実行
            result = await self.emoji_service.vectorize_all_emojis(
                skip_existing=options.get("skip_existing", False),
                dry_run=options.get("dry_run", False),
                progress_callback=progress_callback,
            )

            # 結果をフォーマット
            blocks = self.modal_handler.create_vectorization_result_blocks(result)
            await self.slack_handler.post_message_with_blocks(
                channel=user_id,  # DMとして送信
                blocks=blocks,
                text=f"✅ Vectorization completed! Processed: {result['processed']}",
            )

        except Exception as e:
            logger.error(f"Vectorization error: {e}")
            error_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ Vectorization failed: {str(e)}",
                    },
                }
            ]
            await self.slack_handler.post_message_with_blocks(
                channel=user_id,
                blocks=error_blocks,
                text="❌ Vectorization error occurred.",
            )

    def _create_help_response(self) -> Dict[str, Any]:
        """ヘルプレスポンスを作成"""
        help_text = """Available commands:
• `/emoji help` - Show this help message
• `/emoji list` - List all emojis (requires VIEWER permission)
• `/emoji add` - Add a new emoji (requires EDITOR permission)
• `/emoji search <term>` - Search for emojis
• `/emoji delete <emoji_code>` - Delete an emoji (requires EDITOR permission)
• `/emoji update <emoji_code>` - Update an emoji (requires EDITOR permission)
• `/emoji vectorize` - Vectorize all emojis (requires ADMIN permission)
• `/emoji stats` - Show emoji statistics"""

        return {"response_type": "ephemeral", "text": help_text}

    def _create_permission_denied_response(
        self, required_permission: Permission = Permission.VIEWER
    ) -> Dict[str, Any]:
        """権限不足レスポンスを作成"""
        return {
            "response_type": "ephemeral",
            "text": f"Permission denied. {required_permission.value.upper()} permission required.",
        }

    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """エラーレスポンスを作成"""
        return {
            "response_type": "ephemeral",
            "text": f"❌ Error: {message}",
        }

    def _create_list_response(self, emojis: List[Any]) -> Dict[str, Any]:
        """絵文字リストレスポンスを作成"""
        if not emojis:
            return {"response_type": "ephemeral", "text": "No emojis found."}

        emoji_list = "\n".join([f"• {e.code} - {e.description}" for e in emojis[:20]])

        return {"response_type": "ephemeral", "text": f"Emoji list:\n{emoji_list}"}

    def _create_search_response(
        self, search_term: str, emojis: List[Any]
    ) -> Dict[str, Any]:
        """検索結果レスポンスを作成"""
        if not emojis:
            return {
                "response_type": "ephemeral",
                "text": f"No emojis found for '{search_term}'.",
            }

        emoji_list = "\n".join([f"• {e.code} - {e.description}" for e in emojis])

        return {
            "response_type": "ephemeral",
            "text": f"Search results for '{search_term}':\n{emoji_list}",
        }

    def _create_stats_response(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """統計情報レスポンスを作成"""
        stats_text = f"""Emoji Statistics:
• Total emojis: {stats['total']}
• Vectorized: {stats['vectorized']}
• Not vectorized: {stats['not_vectorized']}

By category:
"""
        for category, count in stats["by_category"].items():
            stats_text += f"• {category}: {count}\n"

        return {"response_type": "ephemeral", "text": stats_text}

    def _create_add_emoji_modal(self) -> Dict[str, Any]:
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

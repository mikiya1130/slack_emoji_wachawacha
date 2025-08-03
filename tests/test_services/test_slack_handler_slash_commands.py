"""
SlackHandlerのスラッシュコマンド拡張テスト

既存のSlackHandlerクラスにスラッシュコマンド機能を追加するテスト
"""


class TestSlackHandlerSlashCommands:
    """SlackHandlerのスラッシュコマンド機能テスト"""

    def test_slash_command_methods_exist(self):
        """スラッシュコマンド関連メソッドの存在確認"""
        from app.services.slack_handler import SlackHandler

        # 必要なメソッドが存在することを確認
        assert hasattr(SlackHandler, "register_slash_command")
        assert hasattr(SlackHandler, "open_modal")
        assert hasattr(SlackHandler, "respond_to_slash_command")
        assert hasattr(SlackHandler, "update_message")
        assert hasattr(SlackHandler, "send_ephemeral_message")
        assert hasattr(SlackHandler, "open_confirm_dialog")
        assert hasattr(SlackHandler, "register_view_submission_handler")
        assert hasattr(SlackHandler, "register_action_handler")
        assert hasattr(SlackHandler, "post_message_with_blocks")

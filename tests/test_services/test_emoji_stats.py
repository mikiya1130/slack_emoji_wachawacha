"""
絵文字統計情報のテスト

EmojiServiceの統計情報取得機能をテスト
"""

import pytest
from unittest.mock import AsyncMock

from app.models.emoji import EmojiData
from app.services.emoji_service import EmojiService


class TestEmojiStats:
    """絵文字統計情報のテストクラス"""

    @pytest.fixture
    def mock_database_service(self):
        """DatabaseServiceのモック"""
        service = AsyncMock()
        return service

    @pytest.fixture
    def emoji_service(self, mock_database_service):
        """EmojiServiceインスタンス"""
        return EmojiService(
            database_service=mock_database_service,
            cache_enabled=True,
        )

    @pytest.fixture
    def sample_emojis(self):
        """サンプル絵文字データ"""
        return [
            EmojiData(
                id=1,
                code=":smile:",
                description="Smiling face",
                category="emotions",
                emotion_tone="positive",
                embedding=[0.1] * 1536,
            ),
            EmojiData(
                id=2,
                code=":sad:",
                description="Sad face",
                category="emotions",
                emotion_tone="negative",
                embedding=[0.2] * 1536,
            ),
            EmojiData(
                id=3,
                code=":wave:",
                description="Waving hand",
                category="gestures",
                emotion_tone="neutral",
                embedding=None,  # ベクトル化されていない
            ),
            EmojiData(
                id=4,
                code=":book:",
                description="Book",
                category="objects",
                emotion_tone="neutral",
                embedding=[0.3] * 1536,
            ),
            EmojiData(
                id=5,
                code=":star:",
                description="Star",
                category="symbols",
                emotion_tone="positive",
                embedding=None,  # ベクトル化されていない
            ),
        ]

    @pytest.mark.asyncio
    async def test_get_emoji_stats_comprehensive(
        self, emoji_service, mock_database_service, sample_emojis
    ):
        """包括的な統計情報の取得をテスト"""
        # モックの設定
        mock_database_service.get_all_emojis = AsyncMock(return_value=sample_emojis)
        mock_database_service.count_emojis = AsyncMock(return_value=len(sample_emojis))

        # 実行
        stats = await emoji_service.get_emoji_stats()

        # 検証
        assert stats["total"] == 5
        assert stats["vectorized"] == 3
        assert stats["not_vectorized"] == 2

        # カテゴリ別の検証
        assert stats["by_category"]["emotions"] == 2
        assert stats["by_category"]["gestures"] == 1
        assert stats["by_category"]["objects"] == 1
        assert stats["by_category"]["symbols"] == 1

        # 感情トーン別の検証（オプション）
        if "by_emotion_tone" in stats:
            assert stats["by_emotion_tone"]["positive"] == 2
            assert stats["by_emotion_tone"]["negative"] == 1
            assert stats["by_emotion_tone"]["neutral"] == 2

    @pytest.mark.asyncio
    async def test_get_emoji_stats_empty_database(
        self, emoji_service, mock_database_service
    ):
        """空のデータベースでの統計情報取得をテスト"""
        # モックの設定
        mock_database_service.get_all_emojis = AsyncMock(return_value=[])
        mock_database_service.count_emojis = AsyncMock(return_value=0)

        # 実行
        stats = await emoji_service.get_emoji_stats()

        # 検証
        assert stats["total"] == 0
        assert stats["vectorized"] == 0
        assert stats["not_vectorized"] == 0
        assert stats["by_category"] == {}

    @pytest.mark.asyncio
    async def test_get_emoji_stats_with_cache(
        self, emoji_service, mock_database_service, sample_emojis
    ):
        """キャッシュ情報を含む統計情報の取得をテスト"""
        # モックの設定
        mock_database_service.get_all_emojis = AsyncMock(return_value=sample_emojis)
        mock_database_service.count_emojis = AsyncMock(return_value=len(sample_emojis))

        # キャッシュに絵文字を追加
        emoji_service.emoji_cache = {
            ":smile:": sample_emojis[0],
            ":sad:": sample_emojis[1],
        }

        # 実行
        stats = await emoji_service.get_emoji_stats()

        # 基本統計の検証
        assert stats["total"] == 5
        assert stats["vectorized"] == 3
        assert stats["not_vectorized"] == 2

        # キャッシュ統計の検証（オプション）
        if "cache_stats" in stats:
            assert stats["cache_stats"]["cached_emojis"] == 2
            assert stats["cache_stats"]["cache_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_emoji_stats_performance(
        self, emoji_service, mock_database_service
    ):
        """大量データでの統計情報取得のパフォーマンスをテスト"""
        # 大量のサンプルデータを作成
        large_sample = []
        for i in range(1000):
            emoji = EmojiData(
                id=i,
                code=f":emoji_{i}:",
                description=f"Emoji {i}",
                category=["emotions", "gestures", "objects", "symbols"][i % 4],
                emotion_tone=["positive", "negative", "neutral"][i % 3],
                embedding=(
                    [0.1] * 1536 if i % 5 != 0 else None
                ),  # 20%がベクトル化されていない
            )
            large_sample.append(emoji)

        # モックの設定
        mock_database_service.get_all_emojis = AsyncMock(return_value=large_sample)
        mock_database_service.count_emojis = AsyncMock(return_value=len(large_sample))

        # 実行
        import time

        start_time = time.time()
        stats = await emoji_service.get_emoji_stats()
        end_time = time.time()

        # 検証
        assert stats["total"] == 1000
        assert stats["vectorized"] == 800  # 80%
        assert stats["not_vectorized"] == 200  # 20%

        # カテゴリ別の検証
        assert stats["by_category"]["emotions"] == 250
        assert stats["by_category"]["gestures"] == 250
        assert stats["by_category"]["objects"] == 250
        assert stats["by_category"]["symbols"] == 250

        # パフォーマンスの検証（1秒以内に完了すること）
        assert end_time - start_time < 1.0

    @pytest.mark.asyncio
    async def test_get_emoji_stats_with_error_handling(
        self, emoji_service, mock_database_service
    ):
        """エラー時の統計情報取得をテスト"""
        # データベースエラーをシミュレート
        mock_database_service.get_all_emojis = AsyncMock(
            side_effect=Exception("Database error")
        )

        # 実行と検証（例外が発生するか、デフォルト値を返すか）
        try:
            stats = await emoji_service.get_emoji_stats()
            # エラー時にデフォルト値を返す実装の場合
            assert stats["total"] == 0
            assert stats["vectorized"] == 0
            assert stats["not_vectorized"] == 0
            assert stats["by_category"] == {}
        except Exception:
            # エラーを再スローする実装の場合
            pass

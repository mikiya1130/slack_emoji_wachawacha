"""
EmojiService単体テスト - TDD RED Phase

このテストは実装前に書かれており、最初は失敗することが期待されます。
EmojiServiceの期待される動作を定義します。

実装要件:
- DatabaseServiceへの依存関係
- 絵文字データの高レベル操作
- JSON/CSVファイルからの一括登録
- ベクトル類似度検索のラッパー
- ビジネスロジックの実装
- キャッシュ機能（オプション）
"""

import pytest
from unittest.mock import Mock, AsyncMock
import json
import os
import tempfile

from app.models.emoji import EmojiData


class TestEmojiServiceInitialization:
    """EmojiServiceの初期化テスト"""

    def test_emoji_service_initialization(self):
        """EmojiServiceの基本初期化テスト - このテストは失敗するはず（RED Phase）"""
        from app.services.emoji_service import EmojiService
        from app.services.database_service import DatabaseService

        mock_db_service = Mock(spec=DatabaseService)
        emoji_service = EmojiService(database_service=mock_db_service)

        # 依存関係が正しく設定されることを確認
        assert emoji_service.database_service == mock_db_service
        assert hasattr(emoji_service, "cache_enabled")

    def test_emoji_service_initialization_with_cache(self):
        """キャッシュ有効での初期化テスト"""
        from app.services.emoji_service import EmojiService
        from app.services.database_service import DatabaseService

        mock_db_service = Mock(spec=DatabaseService)
        emoji_service = EmojiService(
            database_service=mock_db_service, cache_enabled=True, cache_ttl=300
        )

        assert emoji_service.cache_enabled is True
        assert emoji_service.cache_ttl == 300


class TestEmojiServiceBasicOperations:
    """EmojiServiceの基本操作テスト"""

    @pytest.fixture
    def mock_database_service(self):
        """DatabaseServiceのモック"""
        mock_db = AsyncMock()
        return mock_db

    @pytest.fixture
    def mock_emoji_service(self, mock_database_service):
        """EmojiServiceのモック"""
        from app.services.emoji_service import EmojiService

        return EmojiService(database_service=mock_database_service)

    @pytest.fixture
    def sample_emoji_data(self):
        """テスト用絵文字データ"""
        return EmojiData(
            code=":test_emoji:",
            description="Test emoji for service operations",
            category="test",
            emotion_tone="positive",
            usage_scene="testing",
            priority=1,
            embedding=[0.1] * 1536,
        )

    @pytest.mark.asyncio
    async def test_save_emoji_success(self, mock_emoji_service, sample_emoji_data):
        """絵文字保存の成功テスト"""
        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.insert_emoji.return_value = (
            sample_emoji_data
        )

        result = await mock_emoji_service.save_emoji(sample_emoji_data)

        assert result == sample_emoji_data
        mock_emoji_service.database_service.insert_emoji.assert_called_once_with(
            sample_emoji_data
        )

    @pytest.mark.asyncio
    async def test_get_emoji_by_id_success(self, mock_emoji_service, sample_emoji_data):
        """ID指定での絵文字取得テスト"""
        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.get_emoji_by_id.return_value = (
            sample_emoji_data
        )

        result = await mock_emoji_service.get_emoji_by_id(1)

        assert result == sample_emoji_data
        mock_emoji_service.database_service.get_emoji_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_emoji_by_code_success(
        self, mock_emoji_service, sample_emoji_data
    ):
        """コード指定での絵文字取得テスト"""
        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.get_emoji_by_code.return_value = (
            sample_emoji_data
        )

        result = await mock_emoji_service.get_emoji_by_code(":test_emoji:")

        assert result == sample_emoji_data
        mock_emoji_service.database_service.get_emoji_by_code.assert_called_once_with(
            ":test_emoji:"
        )

    @pytest.mark.asyncio
    async def test_update_emoji_success(self, mock_emoji_service, sample_emoji_data):
        """絵文字更新テスト"""
        sample_emoji_data.id = 1
        sample_emoji_data.description = "Updated description"

        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.update_emoji.return_value = (
            sample_emoji_data
        )

        result = await mock_emoji_service.update_emoji(sample_emoji_data)

        assert result == sample_emoji_data
        mock_emoji_service.database_service.update_emoji.assert_called_once_with(
            sample_emoji_data
        )

    @pytest.mark.asyncio
    async def test_delete_emoji_success(self, mock_emoji_service):
        """絵文字削除テスト"""
        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.delete_emoji.return_value = True

        result = await mock_emoji_service.delete_emoji(1)

        assert result is True
        mock_emoji_service.database_service.delete_emoji.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_all_emojis_with_pagination(self, mock_emoji_service):
        """ページネーション付き全絵文字取得テスト"""
        sample_emojis = [
            EmojiData(code=f":emoji_{i}:", description=f"Emoji {i}") for i in range(5)
        ]

        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.get_all_emojis.return_value = sample_emojis

        result = await mock_emoji_service.get_all_emojis(limit=10, offset=0)

        assert result == sample_emojis
        mock_emoji_service.database_service.get_all_emojis.assert_called_once_with(
            limit=10, offset=0
        )

    @pytest.mark.asyncio
    async def test_count_emojis(self, mock_emoji_service):
        """絵文字総数取得テスト"""
        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.count_emojis.return_value = 42

        result = await mock_emoji_service.count_emojis()

        assert result == 42
        mock_emoji_service.database_service.count_emojis.assert_called_once()


class TestEmojiServiceVectorOperations:
    """EmojiServiceのベクトル操作テスト"""

    @pytest.fixture
    def mock_database_service(self):
        """DatabaseServiceのモック"""
        return AsyncMock()

    @pytest.fixture
    def mock_emoji_service(self, mock_database_service):
        """EmojiServiceのモック"""
        from app.services.emoji_service import EmojiService

        return EmojiService(database_service=mock_database_service)

    @pytest.mark.asyncio
    async def test_find_similar_emojis_by_vector(self, mock_emoji_service):
        """ベクトル類似度検索テスト"""
        query_vector = [0.1] * 1536
        expected_emojis = [
            EmojiData(code=":smile:", description="Happy face"),
            EmojiData(code=":joy:", description="Joy face"),
            EmojiData(code=":happy:", description="Happy expression"),
        ]

        # similarity_score属性を追加
        for i, emoji in enumerate(expected_emojis):
            emoji.similarity_score = 0.9 - i * 0.1

        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.find_similar_emojis.return_value = (
            expected_emojis
        )

        result = await mock_emoji_service.find_similar_emojis(query_vector, limit=3)

        assert result == expected_emojis
        mock_emoji_service.database_service.find_similar_emojis.assert_called_once_with(
            query_vector, limit=3, filters=None
        )

    @pytest.mark.asyncio
    async def test_find_similar_emojis_with_filters(self, mock_emoji_service):
        """フィルタ付きベクトル類似度検索テスト"""
        query_vector = [0.1] * 1536
        filters = {"emotion_tone": "positive", "category": "emotions"}
        expected_emojis = [
            EmojiData(
                code=":smile:",
                description="Happy face",
                emotion_tone="positive",
                category="emotions",
            )
        ]
        expected_emojis[0].similarity_score = 0.95

        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.find_similar_emojis.return_value = (
            expected_emojis
        )

        result = await mock_emoji_service.find_similar_emojis(
            query_vector, limit=3, filters=filters
        )

        assert result == expected_emojis
        mock_emoji_service.database_service.find_similar_emojis.assert_called_once_with(
            query_vector, limit=3, filters=filters
        )

    @pytest.mark.asyncio
    async def test_find_similar_emojis_by_text(self, mock_emoji_service):
        """テキストからの類似絵文字検索テスト（OpenAI連携が必要）"""
        query_text = "happy and joyful expression"
        expected_emojis = [
            EmojiData(code=":smile:", description="Happy face"),
            EmojiData(code=":joy:", description="Joy face"),
        ]

        # similarity_score属性を追加
        for i, emoji in enumerate(expected_emojis):
            emoji.similarity_score = 0.9 - i * 0.1

        # find_similar_emojisメソッドをモック
        mock_emoji_service.database_service.find_similar_emojis.return_value = (
            expected_emojis
        )

        # EmojiServiceが内部でOpenAIServiceを使用してベクトル化を行う想定
        result = await mock_emoji_service.find_similar_emojis_by_text(
            query_text, limit=2
        )

        # 実装でOpenAIServiceとの連携をテストする
        assert isinstance(result, list)
        assert len(result) <= 2


class TestEmojiServiceBulkOperations:
    """EmojiServiceの一括操作テスト"""

    @pytest.fixture
    def mock_database_service(self):
        """DatabaseServiceのモック"""
        return AsyncMock()

    @pytest.fixture
    def mock_emoji_service(self, mock_database_service):
        """EmojiServiceのモック"""
        from app.services.emoji_service import EmojiService

        return EmojiService(database_service=mock_database_service)

    @pytest.fixture
    def sample_emoji_json_data(self):
        """テスト用JSON絵文字データ"""
        return [
            {
                "code": ":smile:",
                "description": "Smiling face",
                "category": "emotions",
                "emotion_tone": "positive",
                "usage_scene": "greeting",
                "priority": 1,
            },
            {
                "code": ":thumbsup:",
                "description": "Thumbs up gesture",
                "category": "gestures",
                "emotion_tone": "positive",
                "usage_scene": "approval",
                "priority": 2,
            },
            {
                "code": ":heart:",
                "description": "Red heart",
                "category": "symbols",
                "emotion_tone": "positive",
                "usage_scene": "love",
                "priority": 3,
            },
        ]

    @pytest.mark.asyncio
    async def test_load_emojis_from_json_file(
        self, mock_emoji_service, sample_emoji_json_data
    ):
        """JSONファイルからの絵文字読み込みテスト"""
        # 一時JSONファイルを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_emoji_json_data, f)
            json_file_path = f.name

        try:
            # 読み込み実行
            result = await mock_emoji_service.load_emojis_from_json(json_file_path)

            assert len(result) == 3
            assert all(isinstance(emoji, EmojiData) for emoji in result)
            assert result[0].code == ":smile:"
            assert result[1].code == ":thumbsup:"
            assert result[2].code == ":heart:"

        finally:
            # テンポラリファイルを削除
            os.unlink(json_file_path)

    @pytest.mark.asyncio
    async def test_bulk_save_emojis(self, mock_emoji_service, sample_emoji_json_data):
        """絵文字一括保存テスト"""
        emoji_list = [EmojiData.from_dict(data) for data in sample_emoji_json_data]

        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.batch_insert_emojis.return_value = (
            emoji_list
        )

        result = await mock_emoji_service.bulk_save_emojis(emoji_list)

        assert result == emoji_list
        mock_emoji_service.database_service.batch_insert_emojis.assert_called_once_with(
            emoji_list
        )

    @pytest.mark.asyncio
    async def test_load_and_save_emojis_from_json(
        self, mock_emoji_service, sample_emoji_json_data
    ):
        """JSONファイルからの読み込みと保存の統合テスト"""
        # 一時JSONファイルを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_emoji_json_data, f)
            json_file_path = f.name

        try:
            expected_emojis = [
                EmojiData.from_dict(data) for data in sample_emoji_json_data
            ]

            # DatabaseServiceのmockを設定
            mock_emoji_service.database_service.batch_insert_emojis.return_value = (
                expected_emojis
            )

            # 読み込みと保存を一度に実行
            result = await mock_emoji_service.load_and_save_emojis_from_json(
                json_file_path
            )

            assert len(result) == 3
            mock_emoji_service.database_service.batch_insert_emojis.assert_called_once()

        finally:
            os.unlink(json_file_path)

    @pytest.mark.asyncio
    async def test_export_emojis_to_json(self, mock_emoji_service):
        """絵文字データのJSON出力テスト"""
        sample_emojis = [
            EmojiData(code=":smile:", description="Smiling face", id=1),
            EmojiData(code=":thumbsup:", description="Thumbs up", id=2),
        ]

        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.get_all_emojis.return_value = sample_emojis

        # 一時ファイルパスを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file_path = f.name

        try:
            # エクスポート実行
            await mock_emoji_service.export_emojis_to_json(output_file_path)

            # ファイルの内容を確認
            with open(output_file_path, "r") as f:
                exported_data = json.load(f)

            assert len(exported_data) == 2
            assert exported_data[0]["code"] == ":smile:"
            assert exported_data[1]["code"] == ":thumbsup:"

        finally:
            os.unlink(output_file_path)


class TestEmojiServiceCaching:
    """EmojiServiceのキャッシュ機能テスト"""

    @pytest.fixture
    def mock_database_service(self):
        """DatabaseServiceのモック"""
        return AsyncMock()

    @pytest.fixture
    def mock_emoji_service_with_cache(self, mock_database_service):
        """キャッシュ有効なEmojiServiceのモック"""
        from app.services.emoji_service import EmojiService

        return EmojiService(
            database_service=mock_database_service, cache_enabled=True, cache_ttl=300
        )

    @pytest.mark.asyncio
    async def test_get_emoji_with_cache_miss(self, mock_emoji_service_with_cache):
        """キャッシュミス時の絵文字取得テスト"""
        sample_emoji = EmojiData(code=":smile:", description="Smiling face", id=1)

        # DatabaseServiceのmockを設定
        mock_emoji_service_with_cache.database_service.get_emoji_by_id.return_value = (
            sample_emoji
        )

        # 初回はキャッシュミス
        result = await mock_emoji_service_with_cache.get_emoji_by_id(1)

        assert result == sample_emoji
        mock_emoji_service_with_cache.database_service.get_emoji_by_id.assert_called_once_with(
            1
        )

    @pytest.mark.asyncio
    async def test_get_emoji_with_cache_hit(self, mock_emoji_service_with_cache):
        """キャッシュヒット時の絵文字取得テスト"""
        sample_emoji = EmojiData(code=":smile:", description="Smiling face", id=1)

        # DatabaseServiceのmockを設定
        mock_emoji_service_with_cache.database_service.get_emoji_by_id.return_value = (
            sample_emoji
        )

        # 1回目: キャッシュミス
        result1 = await mock_emoji_service_with_cache.get_emoji_by_id(1)
        assert result1 == sample_emoji

        # 2回目: キャッシュヒット（データベースは呼ばれない）
        result2 = await mock_emoji_service_with_cache.get_emoji_by_id(1)
        assert result2 == sample_emoji

        # データベースは1回だけ呼び出される
        assert (
            mock_emoji_service_with_cache.database_service.get_emoji_by_id.call_count
            == 1
        )

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(self, mock_emoji_service_with_cache):
        """更新時のキャッシュ無効化テスト"""
        sample_emoji = EmojiData(code=":smile:", description="Smiling face", id=1)
        updated_emoji = EmojiData(code=":smile:", description="Very smiling face", id=1)

        # DatabaseServiceのmockを設定
        mock_emoji_service_with_cache.database_service.get_emoji_by_id.return_value = (
            sample_emoji
        )
        mock_emoji_service_with_cache.database_service.update_emoji.return_value = (
            updated_emoji
        )

        # 1回目: データを取得（キャッシュされる）
        result1 = await mock_emoji_service_with_cache.get_emoji_by_id(1)
        assert result1 == sample_emoji

        # データを更新（キャッシュが無効化される）
        await mock_emoji_service_with_cache.update_emoji(updated_emoji)

        # DatabaseServiceのget呼び出しを更新後の値に変更
        mock_emoji_service_with_cache.database_service.get_emoji_by_id.return_value = (
            updated_emoji
        )

        # 2回目: 更新後のデータを取得（キャッシュが無効化されているため再度DBから取得）
        result2 = await mock_emoji_service_with_cache.get_emoji_by_id(1)
        assert result2 == updated_emoji


class TestEmojiServiceBusinessLogic:
    """EmojiServiceのビジネスロジックテスト"""

    @pytest.fixture
    def mock_database_service(self):
        """DatabaseServiceのモック"""
        return AsyncMock()

    @pytest.fixture
    def mock_emoji_service(self, mock_database_service):
        """EmojiServiceのモック"""
        from app.services.emoji_service import EmojiService

        return EmojiService(database_service=mock_database_service)

    @pytest.mark.asyncio
    async def test_get_emoji_stats(self, mock_emoji_service):
        """絵文字統計情報取得テスト"""
        # DatabaseServiceのmockを設定
        mock_emoji_service.database_service.count_emojis.return_value = 100

        stats = await mock_emoji_service.get_emoji_stats()

        assert isinstance(stats, dict)
        assert "total_emojis" in stats
        assert stats["total_emojis"] == 100

    @pytest.mark.asyncio
    async def test_get_emojis_by_category(self, mock_emoji_service):
        """カテゴリ別絵文字取得テスト"""
        # フィルタ機能を使用してカテゴリ別取得
        result = await mock_emoji_service.get_emojis_by_category("emotions")

        assert isinstance(result, list)
        # 実装でフィルタ機能を使用することを期待

    @pytest.mark.asyncio
    async def test_get_emojis_by_emotion_tone(self, mock_emoji_service):
        """感情トーン別絵文字取得テスト"""
        result = await mock_emoji_service.get_emojis_by_emotion_tone("positive")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_validate_emoji_data(self, mock_emoji_service):
        """絵文字データの検証テスト"""
        # 有効なデータ
        valid_emoji = EmojiData(code=":smile:", description="Smiling face")

        # 無効なデータを辞書形式でテスト
        invalid_data_dict = {"code": "invalid", "description": ""}

        # 検証メソッドの実行
        is_valid_1 = await mock_emoji_service.validate_emoji_data(valid_emoji)
        is_valid_2 = await mock_emoji_service.validate_emoji_data(invalid_data_dict)

        assert is_valid_1 is True
        assert is_valid_2 is False


class TestEmojiServiceErrorHandling:
    """EmojiServiceのエラーハンドリングテスト"""

    @pytest.fixture
    def mock_database_service(self):
        """エラーを発生させるDatabaseServiceのモック"""
        mock_db = AsyncMock()
        return mock_db

    @pytest.fixture
    def mock_emoji_service(self, mock_database_service):
        """EmojiServiceのモック"""
        from app.services.emoji_service import EmojiService

        return EmojiService(database_service=mock_database_service)

    @pytest.mark.asyncio
    async def test_handle_database_connection_error(self, mock_emoji_service):
        """データベース接続エラーのハンドリング"""
        from app.services.database_service import DatabaseConnectionError

        # DatabaseServiceでエラーを発生
        mock_emoji_service.database_service.get_emoji_by_id.side_effect = (
            DatabaseConnectionError("Connection failed")
        )

        # EmojiServiceがエラーを適切にハンドリングすることを確認
        with pytest.raises(Exception) as excinfo:
            await mock_emoji_service.get_emoji_by_id(1)

        # EmojiService固有のエラー形式に変換されることを期待
        assert (
            "connection" in str(excinfo.value).lower()
            or "database" in str(excinfo.value).lower()
        )

    @pytest.mark.asyncio
    async def test_handle_invalid_json_file(self, mock_emoji_service):
        """無効なJSONファイルのハンドリング"""
        # 無効なJSONファイルを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {{{")
            invalid_json_file = f.name

        try:
            # 無効なJSONファイルの読み込みでエラーが発生することを確認
            with pytest.raises(Exception) as excinfo:
                await mock_emoji_service.load_emojis_from_json(invalid_json_file)

            # JSON解析エラーが適切にハンドリングされることを確認
            assert (
                "json" in str(excinfo.value).lower()
                or "parse" in str(excinfo.value).lower()
            )

        finally:
            os.unlink(invalid_json_file)

    @pytest.mark.asyncio
    async def test_handle_file_not_found(self, mock_emoji_service):
        """ファイルが見つからない場合のハンドリング"""
        non_existent_file = "/path/to/non/existent/file.json"

        # ファイルが存在しない場合のエラーハンドリング
        with pytest.raises(Exception) as excinfo:
            await mock_emoji_service.load_emojis_from_json(non_existent_file)

        assert (
            "not found" in str(excinfo.value).lower()
            or "file" in str(excinfo.value).lower()
        )


# テスト用のフィクスチャとヘルパー
@pytest.fixture
def sample_emoji_list():
    """テスト用絵文字リスト"""
    return [
        EmojiData(
            code=":smile:",
            description="Smiling face",
            category="emotions",
            emotion_tone="positive",
        ),
        EmojiData(
            code=":frown:",
            description="Frowning face",
            category="emotions",
            emotion_tone="negative",
        ),
        EmojiData(
            code=":thumbsup:",
            description="Thumbs up",
            category="gestures",
            emotion_tone="positive",
        ),
        EmojiData(
            code=":heart:",
            description="Red heart",
            category="symbols",
            emotion_tone="positive",
        ),
        EmojiData(
            code=":fire:",
            description="Fire",
            category="objects",
            emotion_tone="neutral",
        ),
    ]


@pytest.fixture
async def cleanup_test_files():
    """テスト後のファイルクリーンアップ"""
    created_files = []

    def track_file(file_path):
        created_files.append(file_path)
        return file_path

    yield track_file

    # テスト後にファイルをクリーンアップ
    for file_path in created_files:
        if os.path.exists(file_path):
            os.unlink(file_path)

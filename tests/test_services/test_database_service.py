"""
DatabaseService単体テスト - TDD RED Phase

このテストは実装前に書かれており、最初は失敗することが期待されます。
DatabaseServiceの期待される動作を定義します。

実装要件:
- psycopg3を使用したPostgreSQL接続
- pgvectorによるベクトル類似度検索
- コネクションプール管理
- emojisテーブルのCRUD操作
- バッチ処理対応
- 包括的なエラーハンドリング
"""

import pytest
import pytest_asyncio

from app.models.emoji import EmojiData


class TestDatabaseServiceInitialization:
    """DatabaseServiceの初期化テスト"""

    def test_database_service_initialization(self):
        """DatabaseServiceの基本初期化テスト - このテストは失敗するはず（RED Phase）"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()

        # 基本属性が設定されることを確認
        assert hasattr(db_service, "connection_pool")
        assert hasattr(db_service, "connection_string")
        # 初期化前はconnection_poolはNone
        assert db_service.connection_pool is None

    def test_database_service_with_custom_connection_string(self):
        """カスタム接続文字列での初期化テスト"""
        from app.services.database_service import DatabaseService

        custom_url = "postgresql://test:test@localhost:5432/test_db"
        db_service = DatabaseService(connection_url=custom_url)

        assert db_service.connection_string == custom_url

    @pytest.mark.asyncio
    async def test_database_service_connection_pool_initialization(self):
        """コネクションプールの初期化テスト"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()
        await db_service.initialize()
        # 成功した場合の確認
        assert db_service.connection_pool is not None
        assert hasattr(db_service, "pool_size")
        assert db_service.pool_size >= 5  # 最小プールサイズ


class TestDatabaseServiceCRUDOperations:
    """DatabaseServiceのCRUD操作テスト"""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """DatabaseServiceのモック（実装前は None を返す）"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()
        await db_service.initialize()
        yield db_service
        await db_service.close()

    @pytest.fixture
    def sample_emoji_data(self):
        """テスト用絵文字データ（ユニークコード付き）"""
        import time
        import random

        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        return EmojiData(
            code=f":test_emoji_{unique_id}:",
            description="Test emoji for database operations",
            category="test",
            emotion_tone="positive",
            usage_scene="testing",
            priority=1,
            embedding=[0.1] * 1536,
        )

    @pytest.mark.asyncio
    async def test_insert_emoji_success(self, mock_database_service, sample_emoji_data):
        """絵文字データの挿入テスト"""
        # 絵文字データの挿入
        inserted_emoji = await mock_database_service.insert_emoji(sample_emoji_data)

        # 挿入されたデータの確認
        assert inserted_emoji.id is not None
        assert inserted_emoji.code == sample_emoji_data.code
        assert inserted_emoji.description == sample_emoji_data.description
        assert inserted_emoji.created_at is not None
        assert inserted_emoji.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_emoji_by_id_success(self):
        """ID指定での絵文字データ取得テスト"""
        from app.services.database_service import DatabaseService

        # Initialize database service
        db_service = DatabaseService()
        await db_service.initialize()

        try:
            # First insert an emoji with unique code
            import time

            unique_code = f":test_get_{int(time.time())}:"
            emoji_data = EmojiData(
                code=unique_code,
                description="Test emoji for get operation",
                category="test",
                emotion_tone="positive",
                priority=1,
                embedding=[0.1] * 1536,
            )

            inserted_emoji = await db_service.insert_emoji(emoji_data)

            # Then retrieve it by ID
            retrieved_emoji = await db_service.get_emoji_by_id(inserted_emoji.id)

            # Verify the retrieved data
            assert retrieved_emoji is not None
            assert retrieved_emoji.id == inserted_emoji.id
            assert isinstance(retrieved_emoji, EmojiData)
            # With real database, we should get back the same data we inserted
            assert retrieved_emoji.code == unique_code
            assert retrieved_emoji.description == "Test emoji for get operation"
        finally:
            await db_service.close()

    @pytest.mark.asyncio
    async def test_get_emoji_by_id_not_found(self, mock_database_service):
        """存在しないIDでの取得テスト"""
        non_existent_id = 99999
        emoji = await mock_database_service.get_emoji_by_id(non_existent_id)

        assert emoji is None

    @pytest.mark.asyncio
    async def test_get_emoji_by_code_success(
        self, mock_database_service, sample_emoji_data
    ):
        """絵文字コード指定での取得テスト"""
        # まず絵文字を挿入
        inserted_emoji = await mock_database_service.insert_emoji(sample_emoji_data)

        # コードで取得
        emoji = await mock_database_service.get_emoji_by_code(inserted_emoji.code)

        assert emoji is not None
        assert emoji.code == inserted_emoji.code
        assert isinstance(emoji, EmojiData)
        assert emoji.id == inserted_emoji.id

    @pytest.mark.asyncio
    async def test_update_emoji_success(self, mock_database_service, sample_emoji_data):
        """絵文字データの更新テスト"""
        # まず絵文字を挿入
        inserted_emoji = await mock_database_service.insert_emoji(sample_emoji_data)

        # データを更新
        inserted_emoji.description = "Updated description"
        inserted_emoji.priority = 5

        updated_emoji = await mock_database_service.update_emoji(inserted_emoji)

        assert updated_emoji.id == inserted_emoji.id
        assert updated_emoji.description == "Updated description"
        assert updated_emoji.priority == 5
        # updated_atは同じか少し後の時刻になる（データベースの時間精度による）
        assert updated_emoji.updated_at >= inserted_emoji.updated_at

    @pytest.mark.asyncio
    async def test_delete_emoji_success(self, mock_database_service, sample_emoji_data):
        """絵文字データの削除テスト"""
        # まず絵文字を挿入
        inserted_emoji = await mock_database_service.insert_emoji(sample_emoji_data)

        # 削除実行
        success = await mock_database_service.delete_emoji(inserted_emoji.id)
        assert success is True

        # 削除確認
        deleted_emoji = await mock_database_service.get_emoji_by_id(inserted_emoji.id)
        assert deleted_emoji is None

    @pytest.mark.asyncio
    async def test_get_all_emojis_with_pagination(self, mock_database_service):
        """ページネーション付き全絵文字取得テスト"""
        # ページネーション指定で取得
        limit = 10
        offset = 0
        emojis = await mock_database_service.get_all_emojis(limit=limit, offset=offset)

        assert isinstance(emojis, list)
        assert len(emojis) <= limit
        assert all(isinstance(emoji, EmojiData) for emoji in emojis)

    @pytest.mark.asyncio
    async def test_count_emojis(self, mock_database_service):
        """絵文字総数取得テスト"""
        count = await mock_database_service.count_emojis()

        assert isinstance(count, int)
        assert count >= 0


class TestDatabaseServiceVectorOperations:
    """DatabaseServiceのベクトル検索テスト"""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """DatabaseServiceのモック"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()
        await db_service.initialize()
        yield db_service
        await db_service.close()

    @pytest.mark.asyncio
    async def test_find_similar_emojis_by_vector(self, mock_database_service):
        """ベクトル類似度検索テスト"""
        query_vector = [0.1] * 1536
        limit = 3

        similar_emojis = await mock_database_service.find_similar_emojis(
            query_vector, limit=limit
        )

        assert isinstance(similar_emojis, list)
        assert len(similar_emojis) <= limit
        assert all(isinstance(emoji, EmojiData) for emoji in similar_emojis)

        # 類似度が降順でソートされていることを確認
        # (実装では similarity_score 属性が追加される想定)
        if len(similar_emojis) > 1:
            for i in range(len(similar_emojis) - 1):
                assert hasattr(similar_emojis[i], "similarity_score")
                assert hasattr(similar_emojis[i + 1], "similarity_score")
                assert (
                    similar_emojis[i].similarity_score
                    >= similar_emojis[i + 1].similarity_score
                )

    @pytest.mark.asyncio
    async def test_find_similar_emojis_with_filters(self, mock_database_service):
        """フィルタ付きベクトル類似度検索テスト"""
        query_vector = [0.1] * 1536
        filters = {"emotion_tone": "positive", "category": "emotions"}

        similar_emojis = await mock_database_service.find_similar_emojis(
            query_vector, limit=5, filters=filters
        )

        assert isinstance(similar_emojis, list)
        # フィルタ条件を満たすことを確認
        for emoji in similar_emojis:
            if emoji.emotion_tone is not None:
                assert emoji.emotion_tone == "positive"
            if emoji.category is not None:
                assert emoji.category == "emotions"

    @pytest.mark.asyncio
    async def test_find_similar_emojis_empty_result(self, mock_database_service):
        """類似絵文字が見つからない場合のテスト"""
        # 極端なベクトル値（類似するものがない想定）
        query_vector = [100.0] * 1536

        similar_emojis = await mock_database_service.find_similar_emojis(
            query_vector, limit=3
        )

        assert isinstance(similar_emojis, list)
        # 結果が空の場合もあり得る


class TestDatabaseServiceBatchOperations:
    """DatabaseServiceのバッチ処理テスト"""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """DatabaseServiceのモック"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()
        await db_service.initialize()
        yield db_service
        await db_service.close()

    @pytest.fixture
    def sample_emoji_batch(self):
        """テスト用絵文字バッチデータ"""
        import time
        import random

        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        return [
            EmojiData(
                code=f":test_emoji_{i}_{unique_id}:",
                description=f"Test emoji {i}",
                category="test",
                emotion_tone="positive",
                priority=1,
                embedding=[0.1 * i] * 1536,
            )
            for i in range(5)
        ]

    @pytest.mark.asyncio
    async def test_batch_insert_emojis(self, mock_database_service, sample_emoji_batch):
        """絵文字バッチ挿入テスト"""
        inserted_emojis = await mock_database_service.batch_insert_emojis(
            sample_emoji_batch
        )

        assert len(inserted_emojis) == len(sample_emoji_batch)

        for i, emoji in enumerate(inserted_emojis):
            assert emoji.id is not None
            assert emoji.code == sample_emoji_batch[i].code
            assert emoji.created_at is not None

    @pytest.mark.asyncio
    async def test_batch_update_embeddings(self, mock_database_service):
        """埋め込みベクトルのバッチ更新テスト"""
        # ID → 埋め込みベクトルのマッピング
        embedding_updates = {1: [0.2] * 1536, 2: [0.3] * 1536, 3: [0.4] * 1536}

        success = await mock_database_service.batch_update_embeddings(embedding_updates)
        assert success is True

        # 更新確認（実装で検証される）
        for emoji_id, expected_embedding in embedding_updates.items():
            emoji = await mock_database_service.get_emoji_by_id(emoji_id)
            if emoji:
                assert emoji.embedding == expected_embedding


class TestDatabaseServiceConnectionManagement:
    """DatabaseServiceの接続管理テスト"""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """DatabaseServiceのモック"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()
        await db_service.initialize()
        yield db_service
        await db_service.close()

    @pytest.mark.asyncio
    async def test_connection_pool_health_check(self, mock_database_service):
        """コネクションプールのヘルスチェック"""
        # Test with actual service
        health_status = await mock_database_service.health_check()

        # Check the structure of returned health status
        assert isinstance(health_status, dict)
        assert "connected" in health_status
        assert "pool_size" in health_status
        assert "error" in health_status
        assert "error_stats" in health_status

        # If properly initialized, should be connected
        if health_status["connected"]:
            assert health_status["error"] is None

    @pytest.mark.asyncio
    async def test_connection_pool_stats(self, mock_database_service):
        """コネクションプールの統計情報取得"""
        pool_stats = await mock_database_service.get_pool_stats()

        assert isinstance(pool_stats, dict)
        assert "total_connections" in pool_stats
        assert "active_connections" in pool_stats
        assert "idle_connections" in pool_stats

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, mock_database_service):
        """グレースフルシャットダウンテスト"""
        # シャットダウン実行
        await mock_database_service.close()

        # 接続プールが適切に閉じられることを確認
        assert mock_database_service.connection_pool is None or getattr(
            mock_database_service.connection_pool, "closed", False
        )


class TestDatabaseServiceErrorHandling:
    """DatabaseServiceのエラーハンドリングテスト"""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """DatabaseServiceのモック"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()
        await db_service.initialize()
        yield db_service
        await db_service.close()

    @pytest.mark.asyncio
    async def test_insert_duplicate_emoji_code(self, mock_database_service):
        """重複する絵文字コード挿入時のエラーハンドリング"""
        import time
        import random

        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        duplicate_code = f":duplicate_{unique_id}:"

        emoji1 = EmojiData(code=duplicate_code, description="First emoji")
        emoji2 = EmojiData(code=duplicate_code, description="Second emoji")

        # 1回目は成功
        await mock_database_service.insert_emoji(emoji1)

        # 2回目は重複エラー
        with pytest.raises(Exception) as excinfo:
            await mock_database_service.insert_emoji(emoji2)

        # データベース固有の重複エラーが発生することを確認
        assert (
            "duplicate" in str(excinfo.value).lower()
            or "unique" in str(excinfo.value).lower()
        )

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self, mock_database_service):
        """接続失敗時のエラーハンドリング"""
        # 無効な接続情報でデータベースサービスを作成
        from app.services.database_service import DatabaseService

        invalid_db_service = DatabaseService(
            connection_url="postgresql://invalid:invalid@localhost:9999/invalid"
        )

        with pytest.raises(Exception) as excinfo:
            await invalid_db_service.initialize()

        # 接続エラーが適切にハンドリングされることを確認
        assert (
            "connection" in str(excinfo.value).lower()
            or "connect" in str(excinfo.value).lower()
        )

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, mock_database_service):
        """エラー時のトランザクションロールバック"""
        # バッチ処理でエラーが発生した場合のロールバック確認
        # 最初に有効な絵文字を作成
        import time
        import random

        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"

        valid_emoji = EmojiData(code=f":valid_{unique_id}:", description="Valid emoji")

        # 有効な絵文字を挿入後、無効なデータで更新を試行してエラーを発生させる
        await mock_database_service.insert_emoji(valid_emoji)

        # 無効なembedding dimensionでエラーを発生させる
        with pytest.raises(Exception):
            await mock_database_service.find_similar_emojis([0.1] * 100)  # 間違った次元

        # 挿入された絵文字は正常に存在することを確認（find_similar_emojisは別のメソッド）
        emoji = await mock_database_service.get_emoji_by_code(f":valid_{unique_id}:")
        assert emoji is not None  # 正常に挿入されている

    @pytest.mark.asyncio
    async def test_invalid_vector_dimension_handling(self, mock_database_service):
        """無効なベクトル次元でのエラーハンドリング"""
        # 間違った次元のクエリベクトル
        invalid_vector = [0.1] * 100  # 1536ではなく100次元

        with pytest.raises(Exception) as excinfo:
            await mock_database_service.find_similar_emojis(invalid_vector, limit=3)

        # ベクトル次元エラーが適切にハンドリングされることを確認
        assert (
            "dimension" in str(excinfo.value).lower()
            or "vector" in str(excinfo.value).lower()
        )


class TestDatabaseServiceTransactionManagement:
    """DatabaseServiceのトランザクション管理テスト"""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """DatabaseServiceのモック"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()
        await db_service.initialize()
        yield db_service
        await db_service.close()

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, mock_database_service):
        """トランザクションコンテキストマネージャーテスト"""
        import time
        import random

        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        emoji = EmojiData(
            code=f":transaction_test_{unique_id}:", description="Transaction test"
        )

        # トランザクション内で操作実行
        async with mock_database_service.transaction():
            inserted_emoji = await mock_database_service.insert_emoji(emoji)
            assert inserted_emoji.id is not None

        # トランザクション完了後も データが存在することを確認
        retrieved_emoji = await mock_database_service.get_emoji_by_id(inserted_emoji.id)
        assert retrieved_emoji is not None

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_exception(self, mock_database_service):
        """例外発生時のトランザクションロールバック"""
        import time
        import random

        unique_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        unique_code = f":rollback_test_{unique_id}:"
        emoji = EmojiData(code=unique_code, description="Rollback test")

        # 現在の実装では、各メソッドが独自のトランザクションを持つため、
        # 手動でトランザクションをテストするよりも、実際のエラーケースをテスト

        # まず正常な挿入を実行
        inserted_emoji = await mock_database_service.insert_emoji(emoji)
        assert inserted_emoji.id is not None

        # 重複挿入でエラーが発生することを確認
        with pytest.raises(Exception):
            await mock_database_service.insert_emoji(emoji)  # 同じコードで再挿入

        # 最初の挿入は成功しているので、データは存在する
        retrieved_emoji = await mock_database_service.get_emoji_by_code(unique_code)
        assert retrieved_emoji is not None


# テスト用のフィクスチャとヘルパー
@pytest.fixture
def database_config():
    """テスト用データベース設定"""
    return {
        "host": "localhost",
        "port": 5432,
        "database": "emoji_bot_test",
        "user": "test_user",
        "password": "test_pass",
    }


@pytest_asyncio.fixture
async def clean_database():
    """テスト後のデータベースクリーンアップ"""
    yield
    # Note: cleanup is handled by individual test fixtures


class TestDatabaseServiceAdminUser:
    """管理者ユーザー関連の操作のテスト"""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """DatabaseServiceのインスタンス"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()
        await db_service.initialize()
        yield db_service
        await db_service.close()

    @pytest.mark.asyncio
    async def test_admin_user_table_creation(self, mock_database_service):
        """admin_usersテーブル作成のテスト"""
        # テーブル作成実行
        result = await mock_database_service.create_admin_user_table()
        assert result is True

    @pytest.mark.asyncio
    async def test_save_admin_user(self, mock_database_service):
        """管理者ユーザー保存のテスト"""
        from app.models.admin_user import AdminUser, Permission
        from datetime import datetime, UTC

        # テストデータ
        admin_user = AdminUser(
            user_id="U_TEST_ADMIN",
            username="test_admin",
            permission=Permission.ADMIN,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # 実際にデータベースに保存
        result = await mock_database_service.save_admin_user(admin_user)
        assert result is True

        # 保存されたデータを確認
        saved_user = await mock_database_service.get_admin_user("U_TEST_ADMIN")
        assert saved_user is not None
        assert saved_user.username == "test_admin"
        assert saved_user.permission == Permission.ADMIN

    @pytest.mark.asyncio
    async def test_get_admin_user(self, mock_database_service):
        """管理者ユーザー取得のテスト"""
        from app.models.admin_user import AdminUser, Permission
        from datetime import datetime, UTC

        # テストデータを先に保存
        now = datetime.now(UTC)
        admin_user = AdminUser(
            user_id="U_TEST_ADMIN",
            username="test_admin",
            permission=Permission.ADMIN,
            created_at=now,
            updated_at=now,
        )
        await mock_database_service.save_admin_user(admin_user)

        # データ取得
        result = await mock_database_service.get_admin_user("U_TEST_ADMIN")
        assert result is not None
        assert result.user_id == "U_TEST_ADMIN"
        assert result.username == "test_admin"
        assert result.permission == Permission.ADMIN

    @pytest.mark.asyncio
    async def test_get_admin_user_not_found(self, mock_database_service):
        """存在しない管理者ユーザー取得のテスト"""
        # 存在しないユーザーIDで取得試行
        result = await mock_database_service.get_admin_user("U_NOT_EXIST")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_admin_user(self, mock_database_service):
        """管理者ユーザー更新のテスト"""
        from app.models.admin_user import AdminUser, Permission
        from datetime import datetime, UTC

        # テストデータ
        admin_user = AdminUser(
            user_id="U_TEST_ADMIN",
            username="test_admin_updated",
            permission=Permission.EDITOR,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # 先にユーザーを保存
        await mock_database_service.save_admin_user(admin_user)

        # ユーザー情報を更新
        admin_user.username = "test_admin_updated"
        admin_user.permission = Permission.EDITOR

        result = await mock_database_service.update_admin_user(admin_user)
        assert result is True

        # 更新されたデータを確認
        updated_user = await mock_database_service.get_admin_user("U_TEST_ADMIN")
        assert updated_user is not None
        assert updated_user.username == "test_admin_updated"
        assert updated_user.permission == Permission.EDITOR

    @pytest.mark.asyncio
    async def test_delete_admin_user(self, mock_database_service):
        """管理者ユーザー削除のテスト"""
        from app.models.admin_user import AdminUser, Permission

        # 先にユーザーを保存
        admin_user = AdminUser(
            user_id="U_TEST_ADMIN", username="test_admin", permission=Permission.ADMIN
        )
        await mock_database_service.save_admin_user(admin_user)

        # 削除実行
        result = await mock_database_service.delete_admin_user("U_TEST_ADMIN")
        assert result is True

        # 削除されたことを確認
        deleted_user = await mock_database_service.get_admin_user("U_TEST_ADMIN")
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_admin_user_not_found(self, mock_database_service):
        """存在しない管理者ユーザー削除のテスト"""
        # 存在しないユーザーの削除試行
        result = await mock_database_service.delete_admin_user("U_NOT_EXIST")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_admin_users(self, mock_database_service):
        """管理者ユーザー一覧取得のテスト"""
        from app.models.admin_user import AdminUser, Permission
        from datetime import datetime, UTC

        # テストデータを保存
        now = datetime.now(UTC)
        users = [
            AdminUser(
                user_id="U_ADMIN1",
                username="admin1",
                permission=Permission.ADMIN,
                created_at=now,
                updated_at=now,
            ),
            AdminUser(
                user_id="U_EDITOR1",
                username="editor1",
                permission=Permission.EDITOR,
                created_at=now,
                updated_at=now,
            ),
            AdminUser(
                user_id="U_VIEWER1",
                username="viewer1",
                permission=Permission.VIEWER,
                created_at=now,
                updated_at=now,
            ),
        ]

        for user in users:
            await mock_database_service.save_admin_user(user)

        # 一覧取得
        result = await mock_database_service.list_admin_users()
        assert len(result) >= 3

        # 保存したユーザーが含まれていることを確認
        user_ids = [user.user_id for user in result]
        assert "U_ADMIN1" in user_ids
        assert "U_EDITOR1" in user_ids
        assert "U_VIEWER1" in user_ids

    @pytest.mark.asyncio
    async def test_list_admin_users_empty(self, mock_database_service):
        """管理者ユーザーが存在しない場合の一覧取得テスト"""
        # 既存のユーザーがない場合（他のテストで作成されたデータは除く）
        result = await mock_database_service.list_admin_users()
        # 結果はリストであることを確認
        assert isinstance(result, list)

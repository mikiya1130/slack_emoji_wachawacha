"""
DatabaseService - PostgreSQL/pgvector操作サービス

PostgreSQL + pgvectorを使用した絵文字データの管理とベクトル類似度検索を提供します。

主な機能:
- psycopg3を使用したデータベース接続・操作
- pgvectorによるコサイン類似度検索
- コネクションプール管理
- 絵文字データのCRUD操作
- バッチ処理機能
- トランザクション管理
- 包括的なエラーハンドリング
"""

from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional, Tuple
import json

from psycopg_pool import AsyncConnectionPool

from app.models.emoji import EmojiData
from app.config import Config
from app.utils.logging import get_logger

logger = get_logger("database_service")


class DatabaseConnectionError(Exception):
    """データベース接続エラー"""
    pass


class DatabaseOperationError(Exception):
    """データベース操作エラー"""
    pass


class DatabaseService:
    """
    PostgreSQL + pgvectorを使用したデータベースサービス
    
    絵文字データの永続化とベクトル類似度検索を提供します。
    """
    
    def __init__(self, connection_url: Optional[str] = None):
        """
        DatabaseServiceの初期化
        
        Args:
            connection_url: PostgreSQL接続URL（省略時はConfig.DATABASE_URLを使用）
        """
        self.connection_string = connection_url or Config.DATABASE_URL
        self.connection_pool: Optional[AsyncConnectionPool] = None
        self.pool_size = 10  # デフォルトプールサイズ
        self.min_pool_size = 5  # 最小プールサイズ
        self.max_pool_size = 20  # 最大プールサイズ
        
        logger.info(f"DatabaseService initialized with connection: {self._mask_password(self.connection_string)}")
    
    def _mask_password(self, connection_string: str) -> str:
        """接続文字列のパスワードをマスク"""
        try:
            # postgresql://user:password@host:port/database の形式でパスワードをマスク
            if "://" in connection_string and "@" in connection_string:
                parts = connection_string.split("://")
                if len(parts) == 2:
                    scheme = parts[0]
                    rest = parts[1]
                    if "@" in rest:
                        auth_and_host = rest.split("@")
                        if len(auth_and_host) == 2:
                            auth = auth_and_host[0]
                            host_part = auth_and_host[1]
                            if ":" in auth:
                                user_pass = auth.split(":")
                                if len(user_pass) == 2:
                                    return f"{scheme}://{user_pass[0]}:***@{host_part}"
            return connection_string
        except:
            return "***masked***"
    
    async def initialize(self) -> None:
        """
        データベース接続プールを初期化
        
        Raises:
            DatabaseConnectionError: 接続に失敗した場合
        """
        try:
            # コネクションプールの作成
            self.connection_pool = AsyncConnectionPool(
                self.connection_string,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                open=True
            )
            
            # 接続テスト
            async with self.connection_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    if result[0] != 1:
                        raise DatabaseConnectionError("Connection test failed")
            
            logger.info(f"Database connection pool initialized: {self.min_pool_size}-{self.max_pool_size} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise DatabaseConnectionError(f"Database initialization failed: {e}")
    
    async def close(self) -> None:
        """データベース接続プールを閉じる"""
        if self.connection_pool:
            await self.connection_pool.close()
            self.connection_pool = None
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """コネクションプールから接続を取得するコンテキストマネージャー"""
        if not self.connection_pool:
            raise DatabaseConnectionError("Connection pool not initialized")
        
        async with self.connection_pool.connection() as conn:
            yield conn
    
    @asynccontextmanager
    async def transaction(self):
        """トランザクションコンテキストマネージャー"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def health_check(self) -> bool:
        """
        データベース接続のヘルスチェック
        
        Returns:
            bool: 接続が正常な場合True
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """
        コネクションプールの統計情報を取得
        
        Returns:
            Dict[str, Any]: プール統計情報
        """
        if not self.connection_pool:
            return {
                "total_connections": 0,
                "active_connections": 0,
                "idle_connections": 0
            }
        
        # psycopg3のプール統計を取得
        return {
            "total_connections": self.connection_pool.get_stats().get("pool_size", 0),
            "active_connections": self.connection_pool.get_stats().get("pool_available", 0),
            "idle_connections": self.connection_pool.get_stats().get("pool_size", 0) - 
                              self.connection_pool.get_stats().get("pool_available", 0),
            "min_size": self.min_pool_size,
            "max_size": self.max_pool_size
        }
    
    # CRUD操作
    
    async def insert_emoji(self, emoji_data: EmojiData) -> EmojiData:
        """
        絵文字データを挿入
        
        Args:
            emoji_data: 挿入する絵文字データ
            
        Returns:
            EmojiData: 挿入されたデータ（IDと日時が設定される）
            
        Raises:
            DatabaseOperationError: 挿入に失敗した場合
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    # INSERT文の実行
                    query = """
                        INSERT INTO emojis (code, description, category, emotion_tone, 
                                          usage_scene, priority, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at, updated_at
                    """
                    
                    # 埋め込みベクトルをJSON形式に変換（pgvectorの場合は別処理が必要）
                    embedding_json = json.dumps(emoji_data.embedding) if emoji_data.embedding else None
                    
                    await cursor.execute(query, (
                        emoji_data.code,
                        emoji_data.description,
                        emoji_data.category,
                        emoji_data.emotion_tone,
                        emoji_data.usage_scene,
                        emoji_data.priority,
                        embedding_json
                    ))
                    
                    result = await cursor.fetchone()
                    if not result:
                        raise DatabaseOperationError("Insert failed: no result returned")
                    
                    # 結果を設定して返す
                    emoji_data.id = result[0]
                    emoji_data.created_at = result[1]
                    emoji_data.updated_at = result[2]
                    
                    logger.debug(f"Inserted emoji: {emoji_data.code} (ID: {emoji_data.id})")
                    return emoji_data
                    
        except Exception as e:
            logger.error(f"Failed to insert emoji {emoji_data.code}: {e}")
            raise DatabaseOperationError(f"Insert emoji failed: {e}")
    
    async def get_emoji_by_id(self, emoji_id: int) -> Optional[EmojiData]:
        """
        IDで絵文字データを取得
        
        Args:
            emoji_id: 絵文字ID
            
        Returns:
            Optional[EmojiData]: 見つかった絵文字データ、存在しない場合はNone
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    query = """
                        SELECT id, code, description, category, emotion_tone,
                               usage_scene, priority, embedding, created_at, updated_at
                        FROM emojis WHERE id = %s
                    """
                    
                    await cursor.execute(query, (emoji_id,))
                    result = await cursor.fetchone()
                    
                    if not result:
                        return None
                    
                    return self._row_to_emoji_data(result)
                    
        except Exception as e:
            logger.error(f"Failed to get emoji by ID {emoji_id}: {e}")
            raise DatabaseOperationError(f"Get emoji by ID failed: {e}")
    
    async def get_emoji_by_code(self, code: str) -> Optional[EmojiData]:
        """
        コードで絵文字データを取得
        
        Args:
            code: 絵文字コード
            
        Returns:
            Optional[EmojiData]: 見つかった絵文字データ、存在しない場合はNone
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    query = """
                        SELECT id, code, description, category, emotion_tone,
                               usage_scene, priority, embedding, created_at, updated_at
                        FROM emojis WHERE code = %s
                    """
                    
                    await cursor.execute(query, (code,))
                    result = await cursor.fetchone()
                    
                    if not result:
                        return None
                    
                    return self._row_to_emoji_data(result)
                    
        except Exception as e:
            logger.error(f"Failed to get emoji by code {code}: {e}")
            raise DatabaseOperationError(f"Get emoji by code failed: {e}")
    
    async def update_emoji(self, emoji_data: EmojiData) -> EmojiData:
        """
        絵文字データを更新
        
        Args:
            emoji_data: 更新する絵文字データ（IDが必要）
            
        Returns:
            EmojiData: 更新されたデータ
            
        Raises:
            DatabaseOperationError: 更新に失敗した場合
        """
        if not emoji_data.id:
            raise DatabaseOperationError("Emoji ID is required for update")
        
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    query = """
                        UPDATE emojis 
                        SET description = %s, category = %s, emotion_tone = %s,
                            usage_scene = %s, priority = %s, embedding = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING updated_at
                    """
                    
                    embedding_json = json.dumps(emoji_data.embedding) if emoji_data.embedding else None
                    
                    await cursor.execute(query, (
                        emoji_data.description,
                        emoji_data.category,
                        emoji_data.emotion_tone,
                        emoji_data.usage_scene,
                        emoji_data.priority,
                        embedding_json,
                        emoji_data.id
                    ))
                    
                    result = await cursor.fetchone()
                    if not result:
                        raise DatabaseOperationError(f"Update failed: emoji ID {emoji_data.id} not found")
                    
                    emoji_data.updated_at = result[0]
                    
                    logger.debug(f"Updated emoji: {emoji_data.code} (ID: {emoji_data.id})")
                    return emoji_data
                    
        except Exception as e:
            logger.error(f"Failed to update emoji {emoji_data.id}: {e}")
            raise DatabaseOperationError(f"Update emoji failed: {e}")
    
    async def delete_emoji(self, emoji_id: int) -> bool:
        """
        絵文字データを削除
        
        Args:
            emoji_id: 削除する絵文字ID
            
        Returns:
            bool: 削除に成功した場合True
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    query = "DELETE FROM emojis WHERE id = %s"
                    await cursor.execute(query, (emoji_id,))
                    
                    # 削除された行数を確認
                    deleted_count = cursor.rowcount
                    success = deleted_count > 0
                    
                    if success:
                        logger.debug(f"Deleted emoji ID: {emoji_id}")
                    else:
                        logger.warning(f"No emoji found with ID: {emoji_id}")
                    
                    return success
                    
        except Exception as e:
            logger.error(f"Failed to delete emoji {emoji_id}: {e}")
            raise DatabaseOperationError(f"Delete emoji failed: {e}")
    
    async def get_all_emojis(self, limit: int = 100, offset: int = 0) -> List[EmojiData]:
        """
        全絵文字をページネーション付きで取得
        
        Args:
            limit: 取得件数の上限
            offset: オフセット
            
        Returns:
            List[EmojiData]: 絵文字データのリスト
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    query = """
                        SELECT id, code, description, category, emotion_tone,
                               usage_scene, priority, embedding, created_at, updated_at
                        FROM emojis 
                        ORDER BY id
                        LIMIT %s OFFSET %s
                    """
                    
                    await cursor.execute(query, (limit, offset))
                    results = await cursor.fetchall()
                    
                    return [self._row_to_emoji_data(row) for row in results]
                    
        except Exception as e:
            logger.error(f"Failed to get all emojis: {e}")
            raise DatabaseOperationError(f"Get all emojis failed: {e}")
    
    async def count_emojis(self) -> int:
        """
        絵文字の総数を取得
        
        Returns:
            int: 絵文字の総数
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    query = "SELECT COUNT(*) FROM emojis"
                    await cursor.execute(query)
                    result = await cursor.fetchone()
                    return result[0] if result else 0
                    
        except Exception as e:
            logger.error(f"Failed to count emojis: {e}")
            raise DatabaseOperationError(f"Count emojis failed: {e}")
    
    # ベクトル検索操作
    
    async def find_similar_emojis(
        self, 
        query_vector: List[float], 
        limit: int = 3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[EmojiData]:
        """
        ベクトル類似度検索で類似絵文字を取得
        
        Args:
            query_vector: クエリベクトル（1536次元）
            limit: 取得件数上限
            filters: フィルタ条件（emotion_tone, categoryなど）
            
        Returns:
            List[EmojiData]: 類似度順の絵文字リスト
            
        Raises:
            DatabaseOperationError: 検索に失敗した場合
        """
        if len(query_vector) != 1536:
            raise DatabaseOperationError(f"Invalid vector dimension: {len(query_vector)}. Must be 1536")
        
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    # 基本クエリ
                    query = """
                        SELECT id, code, description, category, emotion_tone,
                               usage_scene, priority, embedding, created_at, updated_at,
                               1 - (embedding <=> %s::vector) AS similarity_score
                        FROM emojis 
                        WHERE embedding IS NOT NULL
                        AND embedding <=> %s::vector IS NOT NULL
                    """
                    
                    params = [json.dumps(query_vector), json.dumps(query_vector)]
                    
                    # フィルタ条件を追加
                    if filters:
                        filter_conditions = []
                        for key, value in filters.items():
                            if key in ['emotion_tone', 'category', 'usage_scene']:
                                filter_conditions.append(f"{key} = %s")
                                params.append(value)
                        
                        if filter_conditions:
                            query += " AND " + " AND ".join(filter_conditions)
                    
                    query += " ORDER BY similarity_score DESC LIMIT %s"
                    params.append(limit)
                    
                    await cursor.execute(query, params)
                    results = await cursor.fetchall()
                    
                    emojis = []
                    for row in results:
                        emoji = self._row_to_emoji_data(row[:-1])  # 最後のsimilarity_scoreを除く
                        # NaNチェックを追加
                        score = float(row[-1])
                        if score != score:  # NaN check
                            score = 0.0
                        emoji.similarity_score = score  # similarity_scoreを属性として追加
                        emojis.append(emoji)
                    
                    logger.debug(f"Found {len(emojis)} similar emojis for vector search")
                    return emojis
                    
        except Exception as e:
            logger.error(f"Failed to find similar emojis: {e}")
            raise DatabaseOperationError(f"Vector similarity search failed: {e}")
    
    # バッチ操作
    
    async def batch_insert_emojis(self, emoji_list: List[EmojiData]) -> List[EmojiData]:
        """
        絵文字データのバッチ挿入
        
        Args:
            emoji_list: 挿入する絵文字データのリスト
            
        Returns:
            List[EmojiData]: 挿入されたデータリスト（IDと日時が設定される）
        """
        if not emoji_list:
            return []
        
        try:
            async with self.transaction() as conn:
                async with conn.cursor() as cursor:
                    inserted_emojis = []
                    
                    query = """
                        INSERT INTO emojis (code, description, category, emotion_tone, 
                                          usage_scene, priority, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at, updated_at
                    """
                    
                    for emoji_data in emoji_list:
                        embedding_json = json.dumps(emoji_data.embedding) if emoji_data.embedding else None
                        
                        await cursor.execute(query, (
                            emoji_data.code,
                            emoji_data.description,
                            emoji_data.category,
                            emoji_data.emotion_tone,
                            emoji_data.usage_scene,
                            emoji_data.priority,
                            embedding_json
                        ))
                        
                        result = await cursor.fetchone()
                        if result:
                            emoji_data.id = result[0]
                            emoji_data.created_at = result[1]
                            emoji_data.updated_at = result[2]
                            inserted_emojis.append(emoji_data)
                    
                    logger.info(f"Batch inserted {len(inserted_emojis)} emojis")
                    return inserted_emojis
                    
        except Exception as e:
            logger.error(f"Failed to batch insert emojis: {e}")
            raise DatabaseOperationError(f"Batch insert failed: {e}")
    
    async def batch_update_embeddings(self, embedding_updates: Dict[int, List[float]]) -> bool:
        """
        埋め込みベクトルのバッチ更新
        
        Args:
            embedding_updates: {emoji_id: embedding_vector} の辞書
            
        Returns:
            bool: 更新に成功した場合True
        """
        if not embedding_updates:
            return True
        
        try:
            async with self.transaction() as conn:
                async with conn.cursor() as cursor:
                    query = """
                        UPDATE emojis 
                        SET embedding = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                    
                    for emoji_id, embedding in embedding_updates.items():
                        if len(embedding) != 1536:
                            raise DatabaseOperationError(f"Invalid embedding dimension for ID {emoji_id}")
                        
                        embedding_json = json.dumps(embedding)
                        await cursor.execute(query, (embedding_json, emoji_id))
                    
                    logger.info(f"Batch updated embeddings for {len(embedding_updates)} emojis")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to batch update embeddings: {e}")
            raise DatabaseOperationError(f"Batch update embeddings failed: {e}")
    
    def _row_to_emoji_data(self, row: Tuple) -> EmojiData:
        """
        データベース行をEmojiDataオブジェクトに変換
        
        Args:
            row: データベース行のタプル
            
        Returns:
            EmojiData: 変換されたデータ
        """
        # JSONからembeddingを復元
        embedding = None
        if row[7]:  # embedding フィールド
            try:
                embedding = json.loads(row[7])
            except:
                embedding = None
        
        return EmojiData(
            id=row[0],
            code=row[1],
            description=row[2],
            category=row[3],
            emotion_tone=row[4],
            usage_scene=row[5],
            priority=row[6],
            embedding=embedding,
            created_at=row[8],
            updated_at=row[9]
        )
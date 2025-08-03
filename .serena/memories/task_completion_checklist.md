# タスク完了時のチェックリスト

## コード実装後の必須チェック

### 1. コード品質チェック（厳密な順序で実行）

```bash
# Step 1: コードフォーマット
docker compose exec app black app/ tests/

# Step 2: Lintチェック
docker compose exec app flake8 app/ tests/

# Step 3: 型チェック
docker compose exec app mypy app/

# Step 4: テスト実行（カバレッジ付き）
docker compose exec app pytest --cov=app --cov-report=term-missing
```

### 2. 合格基準

- ✅ Black: 変更なし（already formatted）
- ✅ Flake8: エラーなし
- ✅ Mypy: エラーなし  
- ✅ Pytest: すべて "passed" のみ（failed/skipped/warnings なし）
- ✅ カバレッジ: 80%以上

### 3. エラー時の対応

いずれかのチェックが失敗した場合：
1. エラーを修正
2. **必ずStep 1から再実行**（途中から再開しない）

### 4. 許可されないテスト結果

以下が含まれる場合はタスク未完了：
- `failed` - テストを修正
- `skipped` - skipデコレータを削除または修正
- `xfailed` - 期待される失敗を修正
- `warnings` - 警告を解決
- `errors` - エラーを修正

**唯一許可される形式**:
```
======================== XXX passed in XX.XXs ========================
```

### 5. コミット前の最終確認

- [ ] すべてのチェックが連続でパス
- [ ] 新機能のドキュメント更新
- [ ] CLAUDE.mdの更新（必要な場合）
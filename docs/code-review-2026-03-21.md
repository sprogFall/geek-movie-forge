# Code Review — 最近 5 次提交

**审查日期**: 2026-03-21
**提交范围**: `4cc76d9..1c3240a`（共 5 次提交）

| 提交 | 描述 |
|------|------|
| `1c3240a` | feat(video-generation): 实现异步视频生成任务队列及进度追踪功能 |
| `46f320e` | feat(视频生成): 支持文本素材独立驱动视频生成流程 |
| `13f9a96` | fix(provider): 修复内置提供者更新时保留自定义API密钥和模型的问题 |
| `b576e99` | feat(配置): 添加环境变量支持并增强数据库配置日志 |
| `4cc76d9` | feat: add sqlite and mysql backend persistence |

---

## 已修复的问题

### 1. [Warning] `TokenUsage` 导入被本地类遮蔽 — 已修复

**文件**: `packages/shared/contracts/generations.py:10-26`

第 10 行从 `call_logs` 导入了 `TokenUsage`，但第 22 行又定义了同名本地类，导致导入成为死代码。

**修复**: 将导入重命名为 `_CallLogTokenUsage` 并标记 `noqa: F401`，消除遮蔽。

### 2. [Warning] `api_key` 更新使用 `or` 逻辑错误 — 已修复

**文件**: `services/api/app/services/provider_service.py:147`

```python
# 修复前：空字符串被视为 falsy，无法清空 API key
provider.api_key = payload.api_key or provider.api_key

# 修复后：仅在显式传入 None 时保留旧值
provider.api_key = payload.api_key if payload.api_key is not None else provider.api_key
```

### 3. [Warning] `VideoGenerationTaskRow.task_id` 列宽过窄 — 已修复

**文件**: `packages/db/models.py:108`

`task_id` 列为 `String(32)`，但生成的 ID 格式 `video_task_{hex12}` 已达 23 字符，余量不足。

**修复**: 扩展为 `String(64)`，与其他 ID 列保持一致。

### 4. [Warning] `_looks_like_source_code` 误报率过高 — 已修复

**文件**: `services/api/app/services/generation_service.py:781-795`

含 `"from "` / `"import "` / `"return "` 等单词的正常英文文本（如 "return to the battlefield"）会被误判为源代码。

**修复**: 将 `import`/`from`/`def`/`class`/`return` 归为结构性标记，需命中 ≥3 个才判定为代码（或 ≥2 个且首行以 `:` 结尾）。明确的代码标记（`` ``` ``、`print(`、`console.log(`、`if __name__ ==`）保持单个即触发。

### 5. [Warning] `api.ts` 使用 `import.meta.env`（Vite 约定）而非 Next.js 的 `process.env` — 已修复

**文件**: `apps/frontend/lib/api.ts:23-31`

Next.js 不暴露 `import.meta.env`，应使用 `process.env.NEXT_PUBLIC_*`。

**修复**: 改为 `process.env.NEXT_PUBLIC_API_BASE_URL`。

### 6. [Suggestion] `_parse_timestamp` 在两个服务中重复定义 — 已修复

**文件**: `services/api/app/services/video_generation_task_service.py:26-27` 和 `provider_service.py:71-72`

**修复**: 提取到 `packages/shared/utils.py`，两处改为导入。

---

## 待后续关注的问题（未修复）

### 7. [Critical] 异步方法中使用同步 SQLAlchemy Session

**文件**: `services/api/app/services/video_generation_task_service.py`

`async` 方法和 `asyncio.create_task` 后台协程中直接使用同步 `Session`，会阻塞事件循环。SQLite + `check_same_thread=False` 下并发访问存在线程安全风险。

**建议**: 使用 `sqlalchemy.ext.asyncio.AsyncSession`，或通过 `asyncio.to_thread()` 包装同步 DB 操作。

### 8. [Warning] `_ensure_builtin_providers` 每次 Provider 操作都执行

**文件**: `services/api/app/services/provider_service.py:87-189`

每次 CRUD 调用都会查询数据库检查内置 Provider 是否存在。高流量下造成不必要的 DB 开销。

**建议**: 引入 `self._builtins_seeded: dict[str, bool]` 缓存标记，确认后跳过重复检查。

### 9. [Warning] `test_persistence.py` 使用 `importlib.reload` 较脆弱

**文件**: `services/api/tests/test_persistence.py:18-23`

模块重载方式创建新 `app` 实例，其他模块可能持有旧引用。

**建议**: 改用 app factory 模式。

### 10. [Warning] `_mark_incomplete_tasks_as_interrupted` 在 `__init__` 中无条件执行

**文件**: `services/api/app/services/video_generation_task_service.py:232-248`

服务重建时（含测试中）会将所有 queued/running 任务标记为 failed，无法区分生产重启与测试场景。

**建议**: 通过构造参数 `cleanup_on_init=True` 控制是否执行清理。

### 11. [Suggestion] `list_tasks` 和 `list_video_generation_tasks` 缺少分页

**文件**: `services/api/app/services/video_generation_task_service.py:97-104`

返回所有记录，数据量增长后会产生性能问题。

**建议**: 添加 `limit`/`offset` 分页参数。

---

## 测试验证

修复后全部 **102 个测试通过**（`pytest services/api/tests -q`，耗时 76.80s）。

## 修改文件清单

| 文件 | 修改类型 |
|------|----------|
| `packages/shared/contracts/generations.py` | 修复遮蔽导入 |
| `services/api/app/services/provider_service.py` | 修复 api_key 更新逻辑 + 提取公共函数 |
| `packages/db/models.py` | 扩展 task_id 列宽 |
| `services/api/app/services/generation_service.py` | 改进代码检测逻辑 |
| `apps/frontend/lib/api.ts` | 修复环境变量读取方式 |
| `packages/shared/utils.py` | 新建：提取公共 `parse_timestamp` |
| `services/api/app/services/video_generation_task_service.py` | 导入公共函数 |

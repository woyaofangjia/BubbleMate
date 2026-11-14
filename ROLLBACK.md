# Prompt 回滚操作手册

## 回滚锚点

- `intent_classify/v1`：2026-11-14 从线上原样迁移的意图分类 prompt，迁移时未改文案和调用参数。
- `pure_llm_baseline/v1`：仅用于纯 LLM 对照实验，不影响线上主链路。
- 默认模型由 `LLM_PROVIDER` 和 `LLM_MODEL` 决定；模板默认版本为 `PROMPT_VERSION=v1`。

## 回滚步骤

1. 确认目标模板、模型和 manifest 记录，生产环境设置：

   ```bash
   PROMPT_VERSION=v1
   LLM_PROVIDER=<原提供商>
   LLM_MODEL=<原模型>
   ```

2. 如果代码也有变更，部署包含目标模板的上一版代码或镜像；不要只替换单个运行中文件。
3. 重启全部后端 worker，清除各进程内缓存并加载目标环境变量。
4. 清理共享 Redis 及当前进程中的意图、响应缓存：

   ```bash
   python scripts/flush_intent_cache.py
   ```

5. 用固定问题验证意图和回复，再运行当前模型基线：

   ```bash
   python scripts/run_prompt_baseline.py
   ```

6. 观察意图准确率、LLM 调用失败率、P95 延迟和用户反馈，确认恢复后再开放全部流量。

## 仅评测时切换免费模型

付费模型余额不足时，可在当前 PowerShell 窗口临时使用 `glm-4-flash`，不修改生产环境配置：

```powershell
$env:LLM_MODEL="glm-4-flash"
python scripts/run_prompt_baseline.py
```

报告中的 `model` 会记录实际模型。免费模型结果不能作为其他模型的等价评测结果；恢复生产评测前关闭该窗口或执行 `Remove-Item Env:LLM_MODEL`。

## 缓存注意事项

意图缓存 TTL 为 300 秒，响应缓存 TTL 为 600 秒。脚本可以清理 Redis 和执行脚本进程的内存缓存，但无法清理其他进程的内存缓存，因此**重启全部后端 worker 是完整回滚的必要步骤**，不能只等待 TTL 或只运行清理脚本。

## 新增版本时

新增 `prompts/intent_classify/v<N>.txt`，同步更新 manifest 的版本、作者、日期、模型和变更理由。先运行基线并与上一版对比，再切换 `PROMPT_VERSION`；不要在版本迁移提交中顺带修改 prompt 语义。

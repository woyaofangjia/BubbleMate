# Prompt 发布与回滚操作手册

## 回滚锚点

- `intent_classify/v1`：2026-11-14 从线上原样迁移的意图分类 prompt，迁移时未改文案和调用参数。
- `pure_llm_baseline/v1`：仅用于纯 LLM 对照实验，不影响线上主链路。
- 默认模型由 `LLM_PROVIDER` 和 `LLM_MODEL` 决定；未配置独立发布状态时，模板默认版本为 `PROMPT_VERSION=v1`。

## 独立发布状态

模板和版本记录位于 `prompts/<名称>/`，运行时代码只解析版本，不保存发布文案。发布状态默认写入 `data/prompt_release.json`，可用 `PROMPT_RELEASE_FILE` 覆盖。

- 状态文件存在时优先于 `PROMPT_VERSION`、`PROMPT_CANARY_*` 等环境变量；不要同时用两种方式操作同一环境。
- 多 worker 必须共享同一个可写状态文件，并使用一致的 Redis 配置。
- 每次发布、灰度或回滚都会递增 `revision`。意图和响应缓存键包含 `版本@revision`，即使切回曾经使用的版本，也不会命中上一次发布的旧缓存。

查看当前状态：

```bash
python scripts/prompt_manager.py status
```

## 新增与发布版本

1. 新增 `prompts/intent_classify/v<N>.txt`，并在 `manifest.yaml` 的 `releases` 中登记版本、作者、日期、模型和变更理由。不要在版本迁移提交中顺带修改 prompt 语义。
2. 从所有 manifest 重新生成并校验 changelog：

   ```bash
   python scripts/prompt_manager.py changelog
   python scripts/prompt_manager.py changelog --check
   ```

3. 运行当前模型基线和 CI 门禁：

   ```bash
   python scripts/run_prompt_baseline.py
   python scripts/check_prompt_baseline.py --current <候选报告> --baseline <基线报告>
   ```

4. 先对指定用户或小比例流量灰度，再发布稳定版：

   ```bash
   python scripts/prompt_manager.py canary v2 --percent 10 --users user_001 user_002
   python scripts/prompt_manager.py activate v2 --previous v1
   ```

`activate` 和 `canary` 要求模板存在、版本已登记且 changelog 已更新。命令成功后会清理 Redis 中的意图和响应缓存，并递增发布修订号。执行 CLI 时应使用与后端相同的项目目录、环境变量和 `PROMPT_RELEASE_FILE`。

指定用户始终进入灰度版；比例灰度按灰度版本和用户 ID 稳定哈希。匿名调用未提供用户 ID 时使用稳定版。

## 指标告警与一键回滚

管理后台“Prompt 发布与告警”每 30 秒刷新一次，也可通过带管理鉴权的 `GET /api/admin/prompt-release` 查看。默认监控最近 1 小时：

- 用户反馈通过率较对比版本下降超过 5 个百分点；当前版和对比版均至少 20 条反馈。
- LLM 调用失败率超过 1%；当前版至少 20 次真实 LLM 调用。
- LLM P95 延迟较对比版本劣化超过 20%；两个版本均至少 20 次调用，且基线 P95 大于 0。

灰度期间观察灰度版并与稳定版比较；稳定运行期间观察稳定版并与上一稳定版比较。反馈通过率是正反馈占比，不等同于离线标注测试集准确率。可用 `PROMPT_ALERT_*` 环境变量调整窗口、阈值和最小样本量。离线评测设置 `PROMPT_METRICS_ENABLED=false`，不会写入线上指标。

**当前仅告警，不自动回滚。** 出现告警后，在管理后台确认并点击一键回滚，或执行：

```bash
python scripts/prompt_manager.py rollback
```

回滚规则：

1. 有活跃灰度时，停用灰度并保留当前稳定版。
2. 无活跃灰度时，从稳定版切回 `previous_version`，原稳定版成为新的上一版。
3. 没有可回滚版本时拒绝操作，不改变发布状态。
4. 回滚成功后清理意图和响应缓存并递增修订号，再验证固定问题、监控指标和用户反馈。

LLM 兜底会输出 `prompt_intent` 结构化日志，包含 `prompt_version`、`success`、`intent` 和 `latency_ms`。该日志只覆盖真实 LLM 兜底调用，不代表规则命中或缓存命中的全部请求。

## 环境变量兼容回滚

仅当环境未使用发布状态文件时，通过环境变量回滚：

1. 确认目标模板、模型和 manifest 记录，生产环境设置：

   ```bash
   PROMPT_VERSION=v1
   PROMPT_PREVIOUS_VERSION=<回滚后的上一版>
   LLM_PROVIDER=<原提供商>
   LLM_MODEL=<原模型>
   ```

2. 如果代码也有变更，部署包含目标模板的上一版代码或镜像；不要只替换单个运行中文件。
3. 清空灰度配置并重启全部后端 worker，使所有进程加载相同环境变量。
4. 清理共享 Redis 及当前进程中的意图、响应缓存：

   ```bash
   python scripts/flush_intent_cache.py
   ```

5. 用固定问题验证意图和回复，再运行当前模型基线，确认恢复后逐步开放流量。

已有 `data/prompt_release.json` 时，仅修改上述环境变量不会覆盖文件中的发布状态。

## 仅评测时切换免费模型

付费模型余额不足时，可在当前 PowerShell 窗口临时使用 `glm-4-flash`，不修改生产环境配置：

```powershell
$env:LLM_MODEL="glm-4-flash"
$env:PROMPT_METRICS_ENABLED="false"
python scripts/run_prompt_baseline.py
```

报告中的 `model` 会记录实际模型。免费模型结果不能作为其他模型的等价评测结果；恢复生产评测前关闭该窗口或执行 `Remove-Item Env:LLM_MODEL`。

## 缓存注意事项

意图缓存 TTL 为 300 秒，响应缓存 TTL 为 600 秒。独立发布状态的修订号可隔离其他 worker 中尚未过期的旧进程缓存，但旧条目会保留到 TTL 到期。环境变量兼容模式的修订号固定为 0，因此该模式回滚仍必须重启全部后端 worker。

清理脚本和 CLI 可以清理 Redis；清理脚本只能额外清理执行脚本进程的内存缓存，不能代替多 worker 的发布修订隔离或兼容模式重启。

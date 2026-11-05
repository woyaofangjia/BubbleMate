"""
记忆污染回归测试：否定句、假设句、过期实体、摘要冲突、遗忘入口。

运行：python scripts/test_memory_pollution.py
"""

import os
import sys
import time
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from bubble_agent import (  # noqa: E402
    _extract_entities,
    _compress_history,
    create_memory_store,
    save_message,
    get_context,
    get_user_id,
    forget_user_memory,
)
from storage.database import get_user_preferences  # noqa: E402

DB_PATH = os.path.join(ROOT, "data", "bubblemate.db")
SESSION = f"pollution_test_{int(time.time())}"
results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + (f" | {extra}" if extra else ""))


def clean_test_rows():
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM sessions WHERE session_id LIKE 'pollution_test_%'")
    conn.execute("DELETE FROM users WHERE user_id LIKE 'user_pollution_test_%'")
    conn.commit()
    conn.close()


clean_test_rows()
store = create_memory_store(window_size=3)

# 1. 否定句：不应把被拒绝的值写进记忆
check("否定句-不加珍珠", _extract_entities("我不要珍珠").get("topping") in (None,))
save_message(store, SESSION, "我不要珍珠", "")
_, entities = get_context(store, SESSION)
check("否定句-珍珠未写入记忆", "topping" not in entities, str(entities))

save_message(store, SESSION, "我要三分糖", "")
check("正向前置条件-三分糖已写入", get_context(store, SESSION)[1].get("sugar") == "三分糖")

save_message(store, SESSION, "不要三分糖了", "")
_, entities = get_context(store, SESSION)
check("否定句-删除已有糖度", "sugar" not in entities, str(entities))
check("否定句-同步删除数据库偏好", get_user_preferences(get_user_id(SESSION)).get("sugar") is None)

# 2. 同一句里正向优先于否定
check("正向优先-换成五分糖不要三分糖", _extract_entities("换成五分糖，不要三分糖").get("sugar") == "五分糖")
check("否定句-不要冰仍识别为去冰", _extract_entities("不要冰").get("temperature") == "去冰")

# 3. 假设句 / 第三人称 / 回忆句不写入
for text in ["如果我点三分糖呢", "我朋友想要无糖的", "上次我喝的是七分糖"]:
    check(f"假设/他人/回忆不写入: {text}", "sugar" not in _extract_entities(text), str(_extract_entities(text)))

check("假设分句丢弃、事实分句保留", _extract_entities("如果我要大杯，实际给我中杯").get("size") == "中杯")

# 4. order_id 不再吞手机号
check("手机号不当订单号", "order_id" not in _extract_entities("我的手机号13800138000"))
check("ORD 格式订单号可识别", _extract_entities("订单号 ORD-20260702-001").get("order_id") == "ORD-20260702-001")
check("显式单号可识别", _extract_entities("单号 123456789").get("order_id") == "123456789")

# 5. 记忆项带来源/时间/轮次/置信度
sess = store._get_session(SESSION)
check("用户记忆元数据结构", sess.get("entity_meta", {}).get("drink", {}).get("source") in ("user", "agent") or "entity_meta" in sess)
save_message(store, SESSION, "我要一杯珍珠奶茶", "")
meta = store._get_session(SESSION)["entity_meta"].get("drink", {})
check(
    "用户记忆来源/置信度",
    meta.get("source") == "user" and meta.get("confidence") == 1.0 and "updated_at" in meta and "turn" in meta,
    str(meta),
)

agent_session = SESSION + "_agent"
save_message(store, agent_session, "你好", "推荐珍珠奶茶，18元")
agent_meta = store._get_session(agent_session)["entity_meta"]
check(
    "agent 生成信息降级标注",
    all(agent_meta.get(k, {}).get("source") == "agent" and agent_meta[k].get("confidence") == 0.6 for k in ("drink", "price")),
    str(agent_meta),
)

# 6. 过期实体（订单号/位置）不再注入上下文
ttl_session = SESSION + "_ttl"
save_message(store, ttl_session, "订单号 ORD-20260702-001，在光谷附近", "")
sess = store._get_session(ttl_session)
sess["turn"] = sess["turn"] + 11
store._save_session(ttl_session, sess)
_, entities = get_context(store, ttl_session)
check("过期订单号被过滤", "order_id" not in entities, str(entities))
check("过期位置被过滤", "location" not in entities, str(entities))

# 7. 摘要保留最新值，不保留被否定的旧值
summary = _compress_history(
    [
        {"user": "我要三分糖", "agent": ""},
        {"user": "改成五分糖", "agent": ""},
        {"user": "你好", "agent": ""},
        {"user": "再来一杯", "agent": ""},
    ],
    3,
)[0]["user"]
check("摘要最新值胜出", "sugar=五分糖" in summary and "sugar=三分糖" not in summary, summary)

neg_summary = _compress_history(
    [
        {"user": "我要三分糖", "agent": ""},
        {"user": "不要三分糖了", "agent": ""},
        {"user": "你好", "agent": ""},
        {"user": "再来一杯", "agent": ""},
    ],
    3,
)[0]["user"]
check("摘要不保留被否定值", "sugar=" not in neg_summary, neg_summary)

# 8. 遗忘入口
forget_user_memory(get_user_id(SESSION))
sess = store._get_session(SESSION)
check("遗忘后偏好清空", get_user_preferences(get_user_id(SESSION)) == {})
check("遗忘后实体清空", sess.get("entities") == {} and sess.get("preferences") == {})

clean_test_rows()
failed = [name for name, ok, _ in results if not ok]
print(f"\nSUMMARY: {len(results) - len(failed)} passed, {len(failed)} failed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)

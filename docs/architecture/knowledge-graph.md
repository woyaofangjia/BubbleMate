# 知识图谱系统

## 概述
知识图谱存储投诉类型与解决方案的映射关系，支持自动学习和人工审核。

## 图谱结构

```
┌─────────────────────────────────────────────────────────────┐
│                        知识图谱                               │
│                                                              │
│  [投诉类型]  ──── 1:N ────  [问题变体]                       │
│  (complaint)                 (issue)                         │
│       │                          │                           │
│       │                          │ 1:N                       │
│       │                          ▼                           │
│       │                     [解决方案]                        │
│       │                    (solution)                        │
│       │                          │                           │
│       │                          │ 1:1                       │
│       │                          ▼                           │
│       │                     [补偿方案]                        │
│       │                    (compensation)                    │
│       │                          │                           │
│       ▼                          ▼                           │
│  [投诉记录]  ──── N:1 ────  [知识节点]                       │
│  (complaints)              (knowledge_graph)                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 节点类型

| node_type | 层级 | 说明 |
|-----------|------|------|
| `complaint` | 1 (根) | 投诉类型（如"口味"、"份量"） |
| `issue` | 2 | 具体问题变体（如"口味_太甜"） |
| `solution` | 3 | 解决方案文本 |
| `compensation` | 3 | 补偿方案文本 |

## 数据库表

### knowledge_graph
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| node_name | TEXT | 节点名称 |
| node_type | TEXT | complaint/issue/solution/compensation |
| content | TEXT | 节点内容 |
| parent_id | INTEGER FK | 父节点ID |
| level | INTEGER | 层级 (1/2/3) |
| is_active | BOOLEAN | 是否启用 |

### knowledge_candidates
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| complaint_id | INTEGER FK | 关联投诉 |
| complaint_type | TEXT | 投诉类型 |
| proposed_solution | TEXT | 建议方案 |
| proposed_compensation | TEXT | 建议补偿 |
| status | TEXT | pending/approved/rejected |

## 自动学习流程

```
用户投诉
    │
    ▼
[log_complaint]
    │
    ├── 检查现有知识
    │   └── 找到 → 直接使用
    │
    └── 未找到 → 创建候选 (knowledge_candidates)
            │
            ▼
        [人工审核]
            │
            ├── 批准 → 写入知识图谱
            └── 拒绝 → 标记 rejected
```

## 知识提取

### 获取知识响应
```python
def get_knowledge_response(intent_name):
    category = INTENT_TO_CATEGORY.get(intent_name)
    graph = get_knowledge_graph()
    # 遍历图谱找到匹配的投诉类型
    # 返回 solution 和 compensation
    return solution, compensation
```

### 图谱聚合
```python
def get_knowledge_graph_aggregated():
    # 聚合投诉数量统计
    # 生成 D3 可视化数据
    return {
        'nodes': [...],
        'links': [...],
        'statistics': {...}
    }
```

## 默认方案

### 解决方案
| 类别 | 默认方案 |
|------|---------|
| 口味 | 非常抱歉您对口味不满意，我们会尽快处理 |
| 份量 | 非常抱歉份量不足，我们会补发或补偿 |
| 服务 | 非常抱歉服务态度不佳，已通知门店整改 |
| 配送 | 非常抱歉配送超时，我们会申请超时赔付 |
| 价格 | 非常抱歉价格问题，核实后提供优惠券补偿 |

### 补偿方案
| 类别 | 默认补偿 |
|------|---------|
| 口味 | 免费重做或退款 |
| 份量 | 补发配料或5元优惠券 |
| 服务 | 赠送饮品券 |
| 配送 | 超时赔付或免单 |
| 价格 | 优惠券补偿 |

## 管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/knowledge` | GET | 获取知识图谱 |
| `/api/admin/knowledge/graph` | GET | 获取图谱结构 |
| `/api/admin/knowledge/graph/aggregated` | GET | 聚合统计 |
| `/api/admin/knowledge/review` | POST | 审核知识 |
| `/api/admin/knowledge` | POST | 添加知识节点 |
| `/api/admin/knowledge/relation` | POST | 设置父子关系 |
| `/api/admin/knowledge/{id}` | DELETE | 软删除节点 |
| `/api/admin/candidates` | GET | 获取候选列表 |
| `/api/admin/candidates/{id}/approve` | POST | 批准候选 |
| `/api/admin/candidates/{id}/reject` | POST | 拒绝候选 |

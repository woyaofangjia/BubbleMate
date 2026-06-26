"""
RAG Knowledge Evolution - 自进化知识库
- 从投诉日志中自动提取知识点
- 支持规则提取和LLM提取两种模式
- 自动去重和质量评估
- 定期更新知识库
"""

import json
import os
import re
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class KnowledgePoint:
    id: str
    content: str
    source_type: str
    source_id: str
    category: str
    confidence: float
    created_at: float = field(default_factory=lambda: time.time())


@dataclass
class ComplaintAnalysis:
    complaint_id: str
    complaint_type: str
    description: str
    keywords: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    knowledge_points: List[KnowledgePoint] = field(default_factory=list)


class RAGKnowledgeEvolution:
    """自进化知识库"""

    def __init__(self, chroma_collection=None):
        self.chroma_collection = chroma_collection
        self.complaint_logs: List[Dict] = []
        self.min_confidence = 0.7
        self.max_similarity = 0.95

    def load_complaint_logs(self, log_path: str = None):
        """加载投诉日志"""
        if not log_path:
            log_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "complaints.json")

        log_path = os.path.abspath(log_path)

        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    self.complaint_logs = json.load(f)
                print(f"已加载{len(self.complaint_logs)}条投诉日志")
            except Exception as e:
                print(f"加载投诉日志失败: {e}")

    def analyze_complaint(self, complaint: Dict) -> ComplaintAnalysis:
        """分析单条投诉，提取知识点"""
        analysis = ComplaintAnalysis(
            complaint_id=complaint.get("complaint_id", ""),
            complaint_type=complaint.get("complaint_type", ""),
            description=complaint.get("description", "")
        )

        analysis.keywords = self._extract_keywords(complaint)
        analysis.insights = self._extract_insights(complaint, analysis.keywords)
        analysis.knowledge_points = self._generate_knowledge_points(complaint, analysis)

        return analysis

    def _extract_keywords(self, complaint: Dict) -> List[str]:
        """提取关键词"""
        description = complaint.get("description", "")
        complaint_type = complaint.get("complaint_type", "")

        keywords = []

        drink_keywords = ["芝芝莓莓", "杨枝甘露", "珍珠奶茶", "茉莉绿茶", "柠檬茶",
                          "芝士", "芒果", "草莓", "葡萄", "椰奶", "奶盖"]
        for kw in drink_keywords:
            if kw in description:
                keywords.append(kw)

        sugar_keywords = ["甜", "糖", "无糖", "三分糖", "五分糖", "七分糖"]
        for kw in sugar_keywords:
            if kw in description:
                keywords.append(kw)

        ice_keywords = ["冰", "少冰", "去冰", "温", "热"]
        for kw in ice_keywords:
            if kw in description:
                keywords.append(kw)

        issue_keywords = {
            "口感": ["甜", "苦", "酸", "涩", "淡", "浓"],
            "份量": ["少", "多", "不够", "太多", "分量"],
            "服务": ["态度", "慢", "久", "等待"],
            "配送": ["超时", "慢", "晚", "漏"],
            "价格": ["贵", "便宜", "错", "算"]
        }

        for issue_type, terms in issue_keywords.items():
            if complaint_type == issue_type or any(term in description for term in terms):
                keywords.append(issue_type)

        return list(set(keywords))

    def _extract_insights(self, complaint: Dict, keywords: List[str]) -> List[str]:
        """提取洞察"""
        insights = []
        description = complaint.get("description", "")
        complaint_type = complaint.get("complaint_type", "")

        if "甜" in keywords or "糖" in keywords:
            if "太甜" in description or "很甜" in description:
                insights.append("用户对甜度敏感，建议推荐低糖选项")
            elif "不够甜" in description:
                insights.append("用户喜欢较甜口味")

        if "冰" in keywords:
            if "太多冰" in description or "冰太多" in description:
                insights.append("用户不喜欢多冰，建议默认少冰")
            elif "没有冰" in description:
                insights.append("用户喜欢冰饮")

        if complaint_type == "口感":
            if "珍珠" in keywords:
                insights.append("珍珠口感问题可能需要调整熬煮时间")
            if "奶盖" in keywords:
                insights.append("奶盖厚度或打发程度可能需要优化")

        if complaint_type == "配送":
            if "超时" in description:
                insights.append("配送高峰期需要增加骑手或调整配送范围")

        if complaint_type == "份量":
            insights.append("用户对份量有较高期望，可能需要调整标准")

        return insights

    def _generate_knowledge_points(self, complaint: Dict, analysis: ComplaintAnalysis) -> List[KnowledgePoint]:
        """生成知识点"""
        points = []
        description = complaint.get("description", "")
        complaint_type = complaint.get("complaint_type", "")
        order_id = complaint.get("order_id", "")

        complaint_id = complaint.get("complaint_id", "")
        point_index = 0

        if analysis.insights:
            for insight in analysis.insights:
                points.append(KnowledgePoint(
                    id=f"kp_{complaint_id}_{point_index}",
                    content=insight,
                    source_type="complaint",
                    source_id=complaint_id,
                    category=complaint_type,
                    confidence=0.85
                ))
                point_index += 1

        if complaint_type == "口感" and ("珍珠" in description or "椰果" in description):
            points.append(KnowledgePoint(
                id=f"kp_{complaint_id}_{point_index}",
                content=f"注意{description}中提到的配料口感问题",
                source_type="complaint",
                source_id=complaint_id,
                category="quality",
                confidence=0.8
            ))
            point_index += 1

        if complaint_type == "配送" and "超时" in description:
            points.append(KnowledgePoint(
                id=f"kp_{complaint_id}_{point_index}",
                content="配送超时时应主动联系用户并提供补偿方案",
                source_type="complaint",
                source_id=complaint_id,
                category="service",
                confidence=0.9
            ))
            point_index += 1

        return points

    def is_duplicate(self, content: str) -> bool:
        """检查是否重复"""
        if not self.chroma_collection:
            return False

        results = self.chroma_collection.query(
            query_texts=[content],
            n_results=1,
            include=["distances"]
        )

        if results["distances"] and len(results["distances"][0]) > 0:
            distance = results["distances"][0][0]
            similarity = 1 - distance
            if similarity >= self.max_similarity:
                return True

        return False

    def add_knowledge_points(self, points: List[KnowledgePoint]) -> int:
        """添加知识点到知识库"""
        if not self.chroma_collection:
            return 0

        added_count = 0
        docs_to_add = []
        ids_to_add = []
        metadatas_to_add = []

        for point in points:
            if point.confidence >= self.min_confidence and not self.is_duplicate(point.content):
                docs_to_add.append(point.content)
                ids_to_add.append(point.id)
                metadatas_to_add.append({
                    "source_type": point.source_type,
                    "source_id": point.source_id,
                    "category": point.category,
                    "confidence": point.confidence,
                    "created_at": point.created_at
                })
                added_count += 1

        if docs_to_add:
            self.chroma_collection.add(
                ids=ids_to_add,
                documents=docs_to_add,
                metadatas=metadatas_to_add
            )
            print(f"成功添加{added_count}条新知识点")

        return added_count

    def evolve_from_complaints(self) -> Dict[str, Any]:
        """从投诉日志中自进化知识库"""
        results = {
            "total_complaints": len(self.complaint_logs),
            "analyzed_count": 0,
            "knowledge_points_generated": 0,
            "knowledge_points_added": 0,
            "insights_found": 0
        }

        all_points = []
        all_insights = []

        for complaint in self.complaint_logs:
            analysis = self.analyze_complaint(complaint)
            results["analyzed_count"] += 1
            all_points.extend(analysis.knowledge_points)
            all_insights.extend(analysis.insights)

        results["knowledge_points_generated"] = len(all_points)
        results["insights_found"] = len(all_insights)

        added_count = self.add_knowledge_points(all_points)
        results["knowledge_points_added"] = added_count

        return results

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计"""
        if not self.chroma_collection:
            return {"count": 0}

        count = self.chroma_collection.count()

        results = self.chroma_collection.get(include=["metadatas"])
        categories = {}
        source_types = {}

        if results.get("metadatas"):
            for meta in results["metadatas"]:
                cat = meta.get("category", "unknown")
                categories[cat] = categories.get(cat, 0) + 1
                src = meta.get("source_type", "unknown")
                source_types[src] = source_types.get(src, 0) + 1

        return {
            "total_count": count,
            "categories": categories,
            "source_types": source_types
        }

    def query_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """查询知识库"""
        if not self.chroma_collection:
            return []

        results = self.chroma_collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        knowledge_list = []
        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i] if results["distances"] else 1.0
            meta = results["metadatas"][0][i] if results["metadatas"] else {}

            knowledge_list.append({
                "content": doc,
                "score": 1 - distance,
                "category": meta.get("category", ""),
                "source_type": meta.get("source_type", ""),
                "confidence": meta.get("confidence", 0.0)
            })

        return sorted(knowledge_list, key=lambda x: x["score"], reverse=True)


def generate_sample_complaints() -> List[Dict]:
    """生成示例投诉日志"""
    return [
        {
            "complaint_id": "CMP-001",
            "user_id": "user_001",
            "order_id": "12345",
            "complaint_type": "口感",
            "description": "芝芝莓莓太甜了，喝不下去，希望下次能调整甜度",
            "status": "resolved",
            "created_at": "2024-01-15 10:30:00",
            "resolved_at": "2024-01-15 11:00:00"
        },
        {
            "complaint_id": "CMP-002",
            "user_id": "user_002",
            "order_id": "67890",
            "complaint_type": "份量",
            "description": "珍珠奶茶的珍珠太少了，几乎喝不到，希望能多加一点",
            "status": "pending",
            "created_at": "2024-01-15 12:00:00"
        },
        {
            "complaint_id": "CMP-003",
            "user_id": "user_003",
            "order_id": "11111",
            "complaint_type": "配送",
            "description": "外卖超时半小时，饮品都凉了，体验很差",
            "status": "resolved",
            "created_at": "2024-01-15 14:30:00",
            "resolved_at": "2024-01-15 15:00:00"
        },
        {
            "complaint_id": "CMP-004",
            "user_id": "user_004",
            "order_id": "22222",
            "complaint_type": "口感",
            "description": "杨枝甘露的芒果不够新鲜，有酸味，希望能换新鲜芒果",
            "status": "pending",
            "created_at": "2024-01-15 16:00:00"
        },
        {
            "complaint_id": "CMP-005",
            "user_id": "user_005",
            "order_id": "33333",
            "complaint_type": "服务",
            "description": "门店服务员态度不好，问问题爱答不理的",
            "status": "resolved",
            "created_at": "2024-01-15 18:00:00",
            "resolved_at": "2024-01-15 18:30:00"
        },
        {
            "complaint_id": "CMP-006",
            "user_id": "user_006",
            "order_id": "44444",
            "complaint_type": "口感",
            "description": "珍珠太硬了，嚼不动，应该是煮的时间不够",
            "status": "pending",
            "created_at": "2024-01-15 19:30:00"
        },
        {
            "complaint_id": "CMP-007",
            "user_id": "user_007",
            "order_id": "55555",
            "complaint_type": "配送",
            "description": "收到的饮品漏了一半，包装需要改进",
            "status": "resolved",
            "created_at": "2024-01-15 20:00:00",
            "resolved_at": "2024-01-15 20:30:00"
        },
        {
            "complaint_id": "CMP-008",
            "user_id": "user_008",
            "order_id": "66666",
            "complaint_type": "价格",
            "description": "小程序显示的价格和门店不一样，贵了2元",
            "status": "pending",
            "created_at": "2024-01-15 21:00:00"
        }
    ]


def save_sample_complaints(log_path: str = None):
    """保存示例投诉日志"""
    if not log_path:
        log_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "complaints.json")

    log_path = os.path.abspath(log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    complaints = generate_sample_complaints()
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(complaints, f, ensure_ascii=False, indent=2)

    print(f"示例投诉日志已保存到: {log_path}")


def test_rag_evolution():
    """测试自进化知识库"""
    import chromadb

    persist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chromadb")
    os.makedirs(persist_dir, exist_ok=True)

    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(name="bubblemate_knowledge")

    evolution = RAGKnowledgeEvolution(collection)

    save_sample_complaints()
    evolution.load_complaint_logs()

    print("\n" + "=" * 60)
    print("RAG自进化知识库测试")
    print("=" * 60)

    results = evolution.evolve_from_complaints()
    print(f"\n进化结果:")
    print(f"- 总投诉数: {results['total_complaints']}")
    print(f"- 分析数量: {results['analyzed_count']}")
    print(f"- 生成知识点: {results['knowledge_points_generated']}")
    print(f"- 新增知识点: {results['knowledge_points_added']}")
    print(f"- 发现洞察: {results['insights_found']}")

    stats = evolution.get_knowledge_stats()
    print(f"\n知识库统计:")
    print(f"- 总记录数: {stats['total_count']}")
    print(f"- 分类分布: {stats['categories']}")
    print(f"- 来源类型: {stats['source_types']}")

    print(f"\n查询测试:")
    queries = ["甜度问题", "珍珠口感", "配送超时", "服务态度"]
    for query in queries:
        results = evolution.query_knowledge(query, top_k=2)
        print(f"\n查询: '{query}'")
        if results:
            for i, item in enumerate(results):
                print(f"  {i+1}. {item['content']} (相似度: {item['score']:.2f})")
        else:
            print("  无匹配结果")


if __name__ == "__main__":
    test_rag_evolution()
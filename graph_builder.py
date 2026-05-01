"""
引用图构建器 — 用 NetworkX 建立论文级和方法级图谱
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import networkx as nx
from typing import Optional
from scholar import search_papers, get_paper, get_paper_references, get_paper_citations
from config import MAX_PAPERS, MAX_CITATION_DEPTH, YEAR_RANGE


class CitationGraph:
    """论文引用图 + 方法演化图"""

    def __init__(self):
        self.paper_graph = nx.DiGraph()   # 论文级引用图
        self.method_graph = nx.DiGraph()  # 方法级演化图
        self.paper_meta = {}              # paperId -> metadata
        self.method_meta = {}             # methodId -> metadata
        self._visited = set()

    def seed_from_search(self, query: str, limit: int = 20):
        """从搜索结果初始化图"""
        papers = search_papers(query, limit=limit, year_range=YEAR_RANGE)
        print(f"  搜索到 {len(papers)} 篇论文")
        for p in papers:
            pid = p["paperId"]
            self.paper_meta[pid] = {
                "title": p.get("title", ""),
                "year": p.get("year"),
                "citations": p.get("citationCount", 0),
                "abstract": p.get("abstract", ""),
                "authors": [a.get("name", "") for a in (p.get("authors") or [])[:3]],
            }
            self.paper_graph.add_node(pid)
        return papers

    def expand_citations(self, depth: int = 1, max_per_paper: int = 15):
        """沿引用链展开图"""
        current_level = set(self.paper_graph.nodes())
        for d in range(depth):
            next_level = set()
            total = len(current_level)
            for i, pid in enumerate(current_level):
                if pid in self._visited:
                    continue
                self._visited.add(pid)

                if (i + 1) % 10 == 0:
                    print(f"    深度 {d+1}: {i+1}/{total} 已处理")

                # 获取参考文献
                refs = get_paper_references(pid, limit=max_per_paper)
                for ref in refs:
                    rid = ref.get("paperId")
                    if not rid:
                        continue
                    self.paper_graph.add_edge(pid, rid)
                    if rid not in self.paper_meta:
                        self.paper_meta[rid] = {
                            "title": ref.get("title", ""),
                            "year": ref.get("year"),
                            "citations": ref.get("citationCount", 0),
                            "abstract": ref.get("abstract", ""),
                        }
                    next_level.add(rid)

                # 获取被引
                cites = get_paper_citations(pid, limit=max_per_paper)
                for c in cites:
                    cid = c.get("paperId")
                    if not cid:
                        continue
                    self.paper_graph.add_edge(cid, pid)
                    if cid not in self.paper_meta:
                        self.paper_meta[cid] = {
                            "title": c.get("title", ""),
                            "year": c.get("year"),
                            "citations": c.get("citationCount", 0),
                            "abstract": c.get("abstract", ""),
                        }
                    next_level.add(cid)

                import time
                time.sleep(0.3)  # 速率控制

            current_level = next_level - self._visited
            print(f"  深度 {d+1} 完成，新增 {len(current_level)} 篇待探索")

    def get_top_papers(self, n: int = 30) -> list:
        """按引用数排序取 top 论文"""
        papers = [(pid, self.paper_meta.get(pid, {}).get("citations", 0))
                  for pid in self.paper_graph.nodes()]
        papers.sort(key=lambda x: x[1], reverse=True)
        return papers[:n]

    def get_paper_summary(self, pid: str) -> str:
        """生成论文摘要文本（供 LLM 分析用）"""
        meta = self.paper_meta.get(pid, {})
        title = meta.get("title", "Unknown")
        year = meta.get("year", "?")
        abstract = meta.get("abstract", "") or ""
        authors = ", ".join(meta.get("authors", []))
        citations = meta.get("citations", 0)

        # 找引用关系
        refs = list(self.paper_graph.successors(pid))[:10]
        cited_by = list(self.paper_graph.predecessors(pid))[:10]

        ref_titles = [self.paper_meta.get(r, {}).get("title", "") for r in refs]
        cited_titles = [self.paper_meta.get(c, {}).get("title", "") for c in cited_by]

        return f"""Title: {title}
Year: {year} | Citations: {citations} | Authors: {authors}
Abstract: {abstract[:500]}
References: {'; '.join(ref_titles[:5])}
Cited by: {'; '.join(cited_titles[:5])}"""

    def to_dict(self) -> dict:
        """导出为可序列化字典"""
        return {
            "nodes": len(self.paper_graph.nodes()),
            "edges": len(self.paper_graph.edges()),
            "top_papers": [
                {"id": pid, "title": self.paper_meta.get(pid, {}).get("title", ""),
                 "year": self.paper_meta.get(pid, {}).get("year"),
                 "citations": self.paper_meta.get(pid, {}).get("citations", 0)}
                for pid, _ in self.get_top_papers(20)
            ]
        }

    def save(self, path: str):
        """保存图到文件"""
        data = {
            "paper_graph": nx.node_link_data(self.paper_graph),
            "paper_meta": self.paper_meta,
            "method_graph": nx.node_link_data(self.method_graph),
            "method_meta": self.method_meta,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  图谱已保存: {path}")

    def load(self, path: str):
        """从文件加载图"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.paper_graph = nx.node_link_graph(data["paper_graph"])
        self.paper_meta = data.get("paper_meta", {})
        self.method_graph = nx.node_link_graph(data.get("method_graph", {}))
        self.method_meta = data.get("method_meta", {})
        print(f"  图谱已加载: {len(self.paper_graph.nodes())} 篇论文")

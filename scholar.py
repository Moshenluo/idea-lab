"""
Semantic Scholar API 封装
免费 API，无需 key，有速率限制 (100 req/5min)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import requests
from typing import Optional
from config import S2_API_BASE, S2_API_KEY


def _headers():
    h = {"Accept": "application/json"}
    if S2_API_KEY:
        h["x-api-key"] = S2_API_KEY
    return h


def _get(url, params=None, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=_headers(), timeout=15)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 5))
                print(f"  [rate limit] 等待 {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if i == retries - 1:
                print(f"  [error] {e}")
                return None
            time.sleep(2)
    return None


def search_papers(query: str, limit: int = 20, year_range: tuple = None) -> list:
    """搜索论文，返回论文列表"""
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": "paperId,title,year,citationCount,authors,abstract,externalIds,references,citations"
    }
    if year_range:
        params["year"] = f"{year_range[0]}-{year_range[1]}"

    data = _get(f"{S2_API_BASE}/paper/search", params)
    if not data or "data" not in data:
        return []
    return data["data"]


def get_paper(paper_id: str, fields: str = None) -> Optional[dict]:
    """获取单篇论文详情"""
    if fields is None:
        fields = "paperId,title,year,citationCount,authors,abstract,references,citations,externalIds"
    return _get(f"{S2_API_BASE}/paper/{paper_id}", {"fields": fields})


def get_paper_references(paper_id: str, limit: int = 50) -> list:
    """获取论文的参考文献"""
    data = _get(f"{S2_API_BASE}/paper/{paper_id}/references", {
        "fields": "paperId,title,year,citationCount,abstract",
        "limit": limit
    })
    if not data or "data" not in data:
        return []
    return [r["citedPaper"] for r in data["data"] if r.get("citedPaper", {}).get("paperId")]


def get_paper_citations(paper_id: str, limit: int = 50) -> list:
    """获取引用了这篇论文的论文"""
    data = _get(f"{S2_API_BASE}/paper/{paper_id}/citations", {
        "fields": "paperId,title,year,citationCount,abstract",
        "limit": limit
    })
    if not data or "data" not in data:
        return []
    return [c["citingPaper"] for c in data["data"] if c.get("citingPaper", {}).get("paperId")]


def batch_papers(paper_ids: list, fields: str = None) -> list:
    """批量获取论文"""
    if fields is None:
        fields = "paperId,title,year,citationCount,abstract,authors"
    data = _get(f"{S2_API_BASE}/paper/batch", {
        "fields": fields
    })
    # batch API 用 POST
    import requests as req
    h = _headers()
    h["Content-Type"] = "application/json"
    try:
        r = req.post(f"{S2_API_BASE}/paper/batch",
                     json={"ids": paper_ids[:500]},
                     params={"fields": fields},
                     headers=h, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [batch error] {e}")
        return []


if __name__ == "__main__":
    # 测试：搜索 GNN 相关论文
    results = search_papers("graph neural network citation analysis", limit=5)
    for p in results:
        print(f"  [{p.get('year', '?')}] {p['title']} (citations: {p.get('citationCount', 0)})")

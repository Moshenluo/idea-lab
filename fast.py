"""
IdeaLab Fast — 不依赖 Semantic Scholar，纯 DeepSeek 驱动
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from datetime import datetime
from config import OUTPUT_DIR, MAX_IDEAS
from analyzer import _chat, _parse_json, generate_ideas, enrich_edges_with_papers
import requests as _req
from scholar import search_paper_by_title
from method_utils import normalize_methods_list, dedupe_edges
from idea_utils import annotate_and_rerank_ideas


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def _notify_progress(callback, stage: str, current: int, total: int, message: str):
    if not callback:
        return
    callback({
        "stage": stage,
        "current": current,
        "total": total,
        "message": message,
    })


def _lookup_paper_url(title: str) -> str:
    """通过 Semantic Scholar 查找论文链接"""
    try:
        match = search_paper_by_title(title, limit=5)
        if match:
            return _canonical_url(match)
    except Exception:
        pass
    return ""


def _canonical_url(paper: dict) -> str:
    ext = paper.get("externalIds", {}) or {}
    arxiv = ext.get("ArXiv")
    if arxiv:
        return f"https://arxiv.org/abs/{arxiv}"
    doi = ext.get("DOI")
    if doi:
        return f"https://doi.org/{doi}"
    return paper.get("url", "") or ""


def _verify_papers(papers: list, progress_callback=None) -> list:
    """用 Semantic Scholar 校验并补全 LLM 返回的论文列表。"""
    verified = []
    seen_titles = set()

    total = max(len(papers), 1)
    processed = 0
    for paper in papers:
        title = (paper.get("title") or "").strip()
        if not title:
            processed += 1
            _notify_progress(progress_callback, "verify", processed, total, "跳过空标题候选")
            continue

        match = search_paper_by_title(title, limit=5)
        if match:
            canonical_title = (match.get("title") or title).strip()
            norm_title = canonical_title.lower()
            if norm_title in seen_titles:
                continue
            seen_titles.add(norm_title)
            verified.append({
                "title": canonical_title,
                "year": match.get("year") or paper.get("year"),
                "authors": ", ".join(a.get("name", "") for a in (match.get("authors") or [])[:3]) or paper.get("authors", ""),
                "abstract": match.get("abstract") or paper.get("abstract", ""),
                "key_method": paper.get("key_method", ""),
                "citations_approx": match.get("citationCount", paper.get("citations_approx", 0)),
                "venue": match.get("venue") or (match.get("publicationVenue") or {}).get("name", "") or paper.get("venue", ""),
                "url": _canonical_url(match) or paper.get("url", ""),
                "paper_id": match.get("paperId", ""),
                "verification_source": "semantic_scholar",
            })
        else:
            norm_title = title.lower()
            if norm_title in seen_titles:
                processed += 1
                _notify_progress(progress_callback, "verify", processed, total, f"跳过重复候选: {title[:36]}")
                continue
            seen_titles.add(norm_title)
            paper["url"] = ""
            paper["verification_source"] = "llm_only"
            verified.append(paper)

        processed += 1
        _notify_progress(progress_callback, "verify", processed, total, f"已校验 {processed}/{total}: {title[:36]}")
        time.sleep(0.2)

    return verified


def _fill_urls(papers: list, progress_callback=None) -> list:
    """为没有 URL 的论文补充链接"""
    total = max(len(papers), 1)
    for idx, p in enumerate(papers, 1):
        if not p.get("url"):
            url = _lookup_paper_url(p.get("title", ""))
            if url:
                p["url"] = url
                print(f"    ✓ 找到链接: {p.get('title','')[:40]}... → {url[:50]}")
            time.sleep(0.3)  # S2 速率控制
        _notify_progress(progress_callback, "url", idx, total, f"补充链接 {idx}/{total}: {(p.get('title','') or '')[:36]}")
    return papers


def deepseek_search_papers(
    query: str,
    n: int = 15,
    progress_callback=None,
    fill_missing_urls: bool = True,
) -> list:
    """用 DeepSeek 召回候选论文，再由 Semantic Scholar 校验。"""
    _notify_progress(progress_callback, "recall_start", 0, 1, "正在调用模型召回候选论文...")
    prompt = f"""你是一个 AI 学术搜索专家。
针对以下研究方向，列出 {n} 篇最重要、最有代表性的论文（2017-2025年）。

研究方向: {query}

输出 JSON 数组，每个元素:
{{
  "title": "论文完整标题",
  "year": 发表年份,
  "authors": "第一作者 et al.",
  "abstract": "一句话核心贡献",
  "key_method": "核心方法名",
  "citations_approx": 大约引用数,
  "venue": "发表venue (如 NeurIPS, ICML, ACL, arXiv)",
  "url": "若非常确定可填写论文链接，否则留空字符串"
}}

规则:
- 按时间排序，从最早的奠基工作到最新进展
- 覆盖该方向的不同子方向/分支
- 包含至少一篇综述论文（如有）
- 只列出真实存在的论文
- 不要编造论文链接；不确定时 url 留空字符串 ""
- 优先保证 title 准确，其次再给 url
- 示例: "url": "https://arxiv.org/abs/1609.02907" (GCN), 或 "url": """""
    resp = _chat(prompt, f"研究方向: {query}", temperature=0.3)
    try:
        candidates = _parse_json(resp)
    except:
        return []
    _notify_progress(progress_callback, "recall", 1, 1, f"模型召回到 {len(candidates)} 篇候选论文")
    verified = _verify_papers(candidates, progress_callback=progress_callback)
    if not fill_missing_urls:
        _notify_progress(progress_callback, "url_skipped", 1, 1, "已跳过二次链接补全，加快生成")
        return verified
    return _fill_urls(verified, progress_callback=progress_callback)


def deepseek_build_evolution(papers: list) -> dict:
    """用 DeepSeek 一次性构建完整演化图"""
    papers_text = "\n".join([
        f"- [{p.get('year','?')}] {p.get('title','')} ({p.get('key_method','')})"
        for p in papers
    ])
    prompt = f"""你是一个 AI 方法演化分析专家。
基于以下论文列表，构建方法演化图谱。

论文列表:
{papers_text}

输出 JSON:
{{
  "methods": [
    {{
      "name": "方法名",
      "category": "architecture|training|optimization|data|evaluation",
      "description": "一句话描述",
      "first_paper": "首次提出的论文标题",
      "year": 起始年份
    }}
  ],
  "evolution_edges": [
    {{
      "source": "源方法名",
      "target": "目标方法名",
      "relation": "extends|improves|replaces|adapts|uses_component",
      "bottleneck": "源方法的瓶颈",
      "mechanism": "目标方法的改进机制",
      "trade_off": "改进的权衡"
    }}
  ],
  "bottlenecks": [
    {{
      "description": "瓶颈描述",
      "affected_methods": ["受影响的方法"],
      "attempts": ["已有解决尝试"],
      "remaining_gap": "仍存在的差距",
      "potential_direction": "突破方向"
    }}
  ]
}}

规则:
- 方法名用领域通用简称 (如 Transformer, BERT, LoRA)
- 演化边要有因果关系，不是简单的引用
- 瓶颈要具体，不要泛泛而谈
- 每个瓶颈必须有至少一个 potential_direction"""
    resp = _chat(prompt, f"请基于论文列表构建方法演化图谱", temperature=0.3)
    try:
        return _parse_json(resp)
    except:
        return {"methods": [], "evolution_edges": [], "bottlenecks": []}


def run_fast(query: str):
    """快速模式：纯 DeepSeek 驱动"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(OUTPUT_DIR, f"fast_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    print(f"\n🔬 IdeaLab Fast Mode")
    print(f"   查询: {query}")
    print(f"   输出: {run_dir}")

    # Step 1: 搜索论文
    step("Step 1/4: DeepSeek 搜索论文")
    papers = deepseek_search_papers(query, n=15)
    print(f"  ✓ 找到 {len(papers)} 篇论文")
    for p in papers[:5]:
        print(f"    [{p.get('year','?')}] {p.get('title','')[:55]}... ({p.get('key_method','')})")

    # Step 2: 构建演化图
    step("Step 2/4: 构建方法演化图")
    graph_data = deepseek_build_evolution(papers)
    methods = normalize_methods_list(graph_data.get("methods", []))
    edges = dedupe_edges([
        {
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "relation": e.get("relation", ""),
            "bottleneck": e.get("bottleneck", ""),
            "mechanism": e.get("mechanism", ""),
            "trade_off": e.get("trade_off", ""),
            "confidence": e.get("confidence", None),
        }
        for e in graph_data.get("evolution_edges", [])
    ])
    edges = dedupe_edges(enrich_edges_with_papers(papers, edges))
    bottlenecks = graph_data.get("bottlenecks", [])
    graph_data["methods"] = methods
    graph_data["evolution_edges"] = edges
    print(f"  ✓ 方法: {len(methods)}, 演化边: {len(edges)}, 瓶颈: {len(bottlenecks)}")

    # Step 3: 生成 Idea
    step("Step 3/4: 生成研究 Idea")

    context = f"""研究方向: {query}

方法演化图:
{json.dumps(graph_data, ensure_ascii=False, indent=2)}

请基于以上信息生成 {MAX_IDEAS} 个创新的研究 idea。"""

    ideas = generate_ideas(context, max_ideas=max(MAX_IDEAS * 2, 6))
    ideas = annotate_and_rerank_ideas(ideas, methods, edges, max_ideas=MAX_IDEAS)
    print(f"  ✓ 生成 {len(ideas)} 个 idea")

    # Step 4: 输出
    step("Step 4/4: 生成报告")

    # 保存 JSON
    result = {
        "query": query,
        "timestamp": timestamp,
        "papers": papers,
        "methods": methods,
        "evolution_edges": edges,
        "bottlenecks": bottlenecks,
        "ideas": ideas,
    }
    result_path = os.path.join(run_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 生成 Markdown 报告
    report_path = os.path.join(run_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# IdeaLab 研究报告\n\n")
        f.write(f"**查询:** {query}\n")
        f.write(f"**时间:** {timestamp}\n")
        f.write(f"**模式:** Fast (DeepSeek-only)\n\n")

        f.write("## 论文基础\n\n")
        for p in papers:
            f.write(f"- **[{p.get('year','?')}] {p.get('title','')}** — {p.get('key_method','')} ({p.get('venue','')})\n")
            f.write(f"  > {p.get('abstract','')}\n\n")

        f.write("## 方法列表\n\n")
        for m in methods:
            f.write(f"- **{m.get('name','')}** ({m.get('category','')}, {m.get('year','')}): {m.get('description','')}\n")
            f.write(f"  - 首次提出: {m.get('first_paper','')}\n\n")

        f.write("## 方法演化图\n\n")
        # 生成文本树
        if edges:
            # 找根节点（没有被作为 target 的）
            targets = set(e.get("target","") for e in edges)
            sources = set(e.get("source","") for e in edges)
            roots = sources - targets
            f.write("```\n")
            for root in roots:
                f.write(f"{root}\n")
                children = [e for e in edges if e.get("source") == root]
                for i, e in enumerate(children):
                    is_last = (i == len(children) - 1)
                    prefix = "└──" if is_last else "├──"
                    f.write(f"  {prefix}→ [{e.get('relation','')}] {e.get('target','')}\n")
                    if e.get("bottleneck"):
                        f.write(f"  {'  ' if is_last else '│ '}    瓶颈: {e.get('bottleneck','')}\n")
            f.write("```\n\n")

        f.write("## 演化关系详情\n\n")
        for e in edges:
            f.write(f"### {e.get('source','')} →[{e.get('relation','')}]→ {e.get('target','')}\n")
            f.write(f"- **瓶颈:** {e.get('bottleneck','')}\n")
            f.write(f"- **机制:** {e.get('mechanism','')}\n")
            f.write(f"- **权衡:** {e.get('trade_off','')}\n\n")
            if e.get("evidence"):
                f.write(f"- **证据:** {e.get('evidence','')}\n\n")
            if e.get("source_paper_titles") or e.get("target_paper_titles"):
                f.write(f"- **论文依据:** {', '.join(e.get('source_paper_titles', [])[:2])} -> {', '.join(e.get('target_paper_titles', [])[:2])}\n\n")

        if bottlenecks:
            f.write("## 已识别瓶颈\n\n")
            for b in bottlenecks:
                f.write(f"### {b.get('description','')}\n")
                f.write(f"- 受影响方法: {', '.join(b.get('affected_methods',[]))}\n")
                f.write(f"- 已有尝试: {', '.join(b.get('attempts',[]))}\n")
                f.write(f"- 残留差距: {b.get('remaining_gap','')}\n")
                f.write(f"- 突破方向: {b.get('potential_direction','')}\n\n")

        f.write("## 研究 Idea\n\n")
        for i, idea in enumerate(ideas, 1):
            f.write(f"### {i}. {idea.get('title','')}\n\n")
            f.write(f"**动机:** {idea.get('motivation','')}\n\n")
            f.write(f"**方法:** {idea.get('approach','')}\n\n")
            f.write(f"**预期贡献:** {idea.get('expected_contribution','')}\n\n")
            f.write(f"**相关方法:** {', '.join(idea.get('related_methods',[]))}\n\n")
            f.write(f"**Gap 类型:** {idea.get('gap_type','')} | **新颖性:** {idea.get('novelty_score','?')}/10 | **可行性:** {idea.get('feasibility_score','?')}/10\n\n")
            if idea.get("novelty_rationale"):
                f.write(f"**Novelty Filter:** {idea.get('novelty_rationale','')}\n\n")
            f.write("---\n\n")

    print(f"\n{'='*60}")
    print(f"  ✅ 完成!")
    print(f"  报告: {report_path}")
    print(f"  数据: {result_path}")
    print(f"{'='*60}")

    # 打印 idea 预览
    print(f"\n  研究 Idea 预览:")
    for i, idea in enumerate(ideas, 1):
        print(f"\n  {i}. {idea.get('title','')}")
        print(f"     类型: {idea.get('gap_type','')} | 新颖性: {idea.get('novelty_score','?')}/10 | 可行性: {idea.get('feasibility_score','?')}/10")

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "graph neural network for citation analysis"
    run_fast(q)

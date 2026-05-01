"""
IdeaLab Fast — 不依赖 Semantic Scholar，纯 DeepSeek 驱动
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from config import OUTPUT_DIR, MAX_IDEAS, S2_API_KEY
from analyzer import _chat, _parse_json, extract_methods, analyze_evolution, generate_ideas, analyze_bottlenecks
import requests as _req


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def _lookup_paper_url(title: str) -> str:
    """通过 Semantic Scholar 查找论文链接（含重试）"""
    headers = {"Accept": "application/json"}
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY
    for attempt in range(3):
        try:
            r = _req.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": title[:100], "limit": 1, "fields": "paperId,externalIds,url"},
                headers=headers,
                timeout=8
            )
            if r.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    p = data[0]
                    ext = p.get("externalIds", {})
                    arxiv = ext.get("ArXiv")
                    if arxiv:
                        return f"https://arxiv.org/abs/{arxiv}"
                    doi = ext.get("DOI")
                    if doi:
                        return f"https://doi.org/{doi}"
                    return p.get("url", "")
        except Exception:
            pass
    return ""

def _fill_urls(papers: list) -> list:
    """通过 S2 验证/替换所有论文 URL（不信任 DeepSeek 生成的链接）"""
    for p in papers:
        title = p.get("title", "")
        if not title:
            continue
        # 始终用 S2 查找真实链接，忽略 DeepSeek 生成的
        url = _lookup_paper_url(title)
        if url:
            old_url = p.get("url", "")
            p["url"] = url
            if old_url and old_url != url:
                print(f"    ✓ 修正链接: {title[:40]}... → {url[:60]}")
            elif not old_url:
                print(f"    ✓ 补充链接: {title[:40]}... → {url[:60]}")
        else:
            if p.get("url"):
                print(f"    ⚠ 未验证: {title[:40]}... (保留原链接)")
            else:
                print(f"    ✗ 无链接: {title[:40]}...")
        time.sleep(1.5)  # S2 速率控制（避免 429）
    return papers


def deepseek_search_papers(query: str, n: int = 15) -> list:
    """用 DeepSeek 搜索并结构化论文信息"""
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
  "url": ""
}}

规则:
- 按时间排序，从最早的奠基工作到最新进展
- 覆盖该方向的不同子方向/分支
- 包含至少一篇综述论文（如有）
- 只列出真实存在的论文
- url 字段留空！系统会自动通过 Semantic Scholar 查找真实链接
- 示例: "url": """""
    resp = _chat(prompt, f"研究方向: {query}", temperature=0.3)
    try:
        return _parse_json(resp)
    except:
        return []


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

    # 补充论文链接
    print("\n  正在查找论文链接...")
    papers = _fill_urls(papers)
    # Step 2: 构建演化图
    step("Step 2/4: 构建方法演化图")
    graph_data = deepseek_build_evolution(papers)
    methods = graph_data.get("methods", [])
    edges = graph_data.get("evolution_edges", [])
    bottlenecks = graph_data.get("bottlenecks", [])
    print(f"  ✓ 方法: {len(methods)}, 演化边: {len(edges)}, 瓶颈: {len(bottlenecks)}")

    # Step 3: 生成 Idea
    step("Step 3/4: 生成研究 Idea")

    context = f"""研究方向: {query}

方法演化图:
{json.dumps(graph_data, ensure_ascii=False, indent=2)}

请基于以上信息生成 {MAX_IDEAS} 个创新的研究 idea。"""

    ideas = generate_ideas(context, max_ideas=MAX_IDEAS)
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

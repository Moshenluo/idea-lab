"""
IdeaLab 主流程 — 从搜索到 idea 生成的完整 pipeline
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime

from config import OUTPUT_DIR, MAX_IDEAS, MAX_CITATION_DEPTH
from graph_builder import CitationGraph
from analyzer import extract_methods, analyze_evolution, generate_ideas, analyze_bottlenecks


def search_and_enrich(query: str, limit: int = 15) -> list:
    """完整模式：用 S2 搜索论文并补充引用信息"""
    from scholar import search_papers
    from fast import _fill_urls

    step("搜索论文 (S2 API)")
    papers = search_papers(query, limit=limit)
    print(f"  找到 {len(papers)} 篇论文")

    # 补充链接
    papers = _fill_urls(papers)
    return papers


def step(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def run_pipeline(query: str, limit: int = 20, depth: int = None):
    """
    完整 pipeline:
    1. 搜索论文
    2. 构建引用图
    3. 提取方法实体
    4. 识别演化关系
    5. 分析瓶颈
    6. 生成 idea
    """
    if depth is None:
        depth = MAX_CITATION_DEPTH

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(OUTPUT_DIR, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    print(f"\n🔬 IdeaLab Pipeline")
    print(f"   查询: {query}")
    print(f"   论文数: {limit}, 引用深度: {depth}")
    print(f"   输出目录: {run_dir}")

    # ─── Step 1: 搜索 + 建图 ───────────────────────────────
    step("Step 1/5: 搜索论文 & 构建引用图")
    graph = CitationGraph()
    graph.seed_from_search(query, limit=limit)
    print(f"  ✓ 初始论文: {len(graph.paper_graph.nodes())} 篇")

    step("Step 1.5: 沿引用链展开")
    graph.expand_citations(depth=depth, max_per_paper=10)
    print(f"  ✓ 图谱规模: {len(graph.paper_graph.nodes())} 节点, {len(graph.paper_graph.edges())} 边")

    # 保存原始图
    graph.save(os.path.join(run_dir, "citation_graph.json"))

    # ─── Step 2: 取 Top 论文 ───────────────────────────────
    step("Step 2/5: 筛选核心论文")
    top_papers = graph.get_top_papers(20)
    print(f"  Top 5 高引论文:")
    for pid, cites in top_papers[:5]:
        title = graph.paper_meta.get(pid, {}).get("title", "?")
        year = graph.paper_meta.get(pid, {}).get("year", "?")
        print(f"    [{year}] {title[:60]}... ({cites} 引用)")

    # ─── Step 3: 方法提取 ──────────────────────────────────
    step("Step 3/5: LLM 提取方法实体")
    methods = {}  # method_name -> info
    paper_methods = {}  # paperId -> [method_names]

    for i, (pid, _) in enumerate(top_papers[:15]):
        summary = graph.get_paper_summary(pid)
        print(f"  [{i+1}/15] 分析: {graph.paper_meta.get(pid, {}).get('title', '?')[:50]}...")

        extracted = extract_methods(summary)
        paper_methods[pid] = []
        for m in extracted:
            name = m.get("name", "unknown")
            methods[name] = m
            paper_methods[pid].append(name)
            # 添加到方法图
            graph.method_graph.add_node(name, **m)

        time.sleep(0.5)

    print(f"  ✓ 提取方法: {len(methods)} 个")

    # ─── Step 4: 演化关系识别 ──────────────────────────────
    step("Step 4/5: 识别方法演化关系")
    evolution_edges = []

    # 遍历引用边，分析有方法关联的论文对
    checked = 0
    for pid in list(paper_methods.keys())[:10]:
        refs = list(graph.paper_graph.successors(pid))[:5]
        for rid in refs:
            if rid not in paper_methods:
                # 为被引论文也提取方法
                summary = graph.get_paper_summary(rid)
                extracted = extract_methods(summary)
                paper_methods[rid] = [m.get("name", "unknown") for m in extracted]
                for m in extracted:
                    methods[m["name"]] = m
                    graph.method_graph.add_node(m["name"], **m)
                time.sleep(0.3)

            if not paper_methods.get(pid) or not paper_methods.get(rid):
                continue

            # 分析演化关系
            a_summary = graph.get_paper_summary(pid)
            b_summary = graph.get_paper_summary(rid)
            evo = analyze_evolution(a_summary, b_summary)

            if evo.get("relation") != "unrelated" and evo.get("confidence", 0) > 0.5:
                for ma in paper_methods[pid]:
                    for mb in paper_methods[rid]:
                        graph.method_graph.add_edge(mb, ma, **evo)
                        evolution_edges.append({
                            "from": mb, "to": ma,
                            "relation": evo.get("relation"),
                            "bottleneck": evo.get("bottleneck", ""),
                            "mechanism": evo.get("mechanism", ""),
                        })
                        print(f"    {mb} --[{evo['relation']}]--> {ma}")

            checked += 1
            time.sleep(0.5)

    print(f"  ✓ 演化边: {len(evolution_edges)} 条")

    # 保存方法图
    graph.save(os.path.join(run_dir, "citation_graph.json"))

    # ─── Step 5: 生成 Idea ────────────────────────────────
    step("Step 5/5: 分析瓶颈 & 生成研究 Idea")

    # 构建演化链文本
    chain_text = ""
    for evo in evolution_edges:
        chain_text += f"- {evo['from']} --[{evo['relation']}]--> {evo['to']}\n"
        if evo.get("bottleneck"):
            chain_text += f"  瓶颈: {evo['bottleneck']}\n"
        if evo.get("mechanism"):
            chain_text += f"  机制: {evo['mechanism']}\n"

    # 瓶颈分析
    if chain_text:
        print("  分析瓶颈中...")
        bottleneck_result = analyze_bottlenecks(chain_text)
        bottlenecks = bottleneck_result.get("bottlenecks", [])
        print(f"  ✓ 发现 {len(bottlenecks)} 个瓶颈")
    else:
        bottlenecks = []

    # 构建生成 context
    context = f"""研究主题: {query}

方法演化链:
{chain_text}

已识别瓶颈:
{json.dumps(bottlenecks, ensure_ascii=False, indent=2)}

方法图谱统计:
- 总方法数: {len(methods)}
- 总演化边: {len(evolution_edges)}
- 核心方法: {', '.join(list(methods.keys())[:20])}"""

    # 生成 idea
    print("  生成研究 idea 中...")
    ideas = generate_ideas(context, max_ideas=MAX_IDEAS)
    print(f"  ✓ 生成 {len(ideas)} 个 idea")

    # ─── 输出结果 ──────────────────────────────────────────
    result = {
        "query": query,
        "timestamp": timestamp,
        "graph_stats": graph.to_dict(),
        "methods": methods,
        "evolution_edges": evolution_edges,
        "bottlenecks": bottlenecks,
        "ideas": ideas,
    }

    result_path = os.path.join(run_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 生成可读报告
    report_path = os.path.join(run_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# IdeaLab 研究报告\n\n")
        f.write(f"**查询:** {query}\n")
        f.write(f"**时间:** {timestamp}\n")
        f.write(f"**论文数:** {len(graph.paper_graph.nodes())}\n")
        f.write(f"**方法数:** {len(methods)}\n")
        f.write(f"**演化边:** {len(evolution_edges)}\n\n")

        f.write(f"## 核心方法\n\n")
        for name, m in methods.items():
            f.write(f"- **{name}** ({m.get('category', '?')}, {m.get('novelty', '?')}): {m.get('description', '')}\n")

        f.write(f"\n## 演化关系\n\n")
        for evo in evolution_edges:
            f.write(f"- **{evo['from']}** →[{evo['relation']}]→ **{evo['to']}**\n")
            if evo.get("bottleneck"):
                f.write(f"  - 瓶颈: {evo['bottleneck']}\n")
            if evo.get("mechanism"):
                f.write(f"  - 机制: {evo['mechanism']}\n")

        if bottlenecks:
            f.write(f"\n## 已识别瓶颈\n\n")
            for b in bottlenecks:
                f.write(f"### {b.get('description', '?')}\n")
                f.write(f"- 受影响方法: {', '.join(b.get('affected_methods', []))}\n")
                f.write(f"- 已有尝试: {', '.join(b.get('attempts', []))}\n")
                f.write(f"- 残留差距: {b.get('remaining_gap', '')}\n")
                f.write(f"- 突破方向: {b.get('potential_direction', '')}\n\n")

        f.write(f"\n## 研究 Idea\n\n")
        for i, idea in enumerate(ideas, 1):
            f.write(f"### {i}. {idea.get('title', '?')}\n\n")
            f.write(f"**动机:** {idea.get('motivation', '')}\n\n")
            f.write(f"**方法:** {idea.get('approach', '')}\n\n")
            f.write(f"**预期贡献:** {idea.get('expected_contribution', '')}\n\n")
            f.write(f"**相关方法:** {', '.join(idea.get('related_methods', []))}\n\n")
            f.write(f"**Gap 类型:** {idea.get('gap_type', '')} | **新颖性:** {idea.get('novelty_score', '?')}/10 | **可行性:** {idea.get('feasibility_score', '?')}/10\n\n")
            f.write(f"---\n\n")

    print(f"\n{'='*60}")
    print(f"  ✅ 完成！")
    print(f"  结果: {result_path}")
    print(f"  报告: {report_path}")
    print(f"{'='*60}")

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "graph neural network for citation analysis"

    run_pipeline(query, limit=15, depth=1)

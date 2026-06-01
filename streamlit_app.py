"""
IdeaLab Streamlit app.

This entrypoint is designed for Streamlit Community Cloud while reusing the
existing research pipeline modules.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
import streamlit.components.v1 as components


def _bootstrap_secrets() -> None:
    """Expose Streamlit secrets as environment variables before local imports."""
    for key in ("DEEPSEEK_API_KEY", "S2_API_KEY"):
        if os.environ.get(key):
            continue
        try:
            value = st.secrets.get(key, "")
        except Exception:
            value = ""
        if value:
            os.environ[key] = str(value)


_bootstrap_secrets()

from analyzer import enrich_edges_with_papers, generate_ideas  # noqa: E402
from config import MAX_IDEAS, OUTPUT_DIR  # noqa: E402
from fast import deepseek_build_evolution, deepseek_search_papers  # noqa: E402
from history import list_runs, get_run  # noqa: E402
from idea_utils import annotate_and_rerank_ideas  # noqa: E402
from method_utils import dedupe_edges, normalize_methods_list  # noqa: E402
from visualizer import generate_graph_html  # noqa: E402


st.set_page_config(
    page_title="IdeaLab",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _write_report(run_dir: str, result: Dict[str, Any]) -> str:
    """Write a compact Markdown report for Streamlit and CLI downloads."""
    path = os.path.join(run_dir, "report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# IdeaLab 研究报告\n\n**查询:** {result.get('query', '')}\n\n")

        f.write("## 论文基础\n\n")
        for p in result.get("papers", []):
            title = p.get("title", "")
            link = p.get("url", "")
            title_md = f"[{title}]({link})" if link else title
            f.write(f"- [{p.get('year', '?')}] **{title_md}** - {p.get('key_method', '')}\n")
            if p.get("abstract"):
                f.write(f"  > {p.get('abstract', '')}\n")
            f.write("\n")

        f.write("## 方法实体\n\n")
        for m in result.get("methods", []):
            f.write(
                f"- **{m.get('name', '')}** "
                f"({m.get('category', '')}, {m.get('year', '')}): "
                f"{m.get('description', '')}\n"
            )

        f.write("\n## 演化关系\n\n")
        for e in result.get("evolution_edges", []):
            f.write(f"### {e.get('source', '')} ->[{e.get('relation', '')}]-> {e.get('target', '')}\n")
            f.write(f"- 瓶颈: {e.get('bottleneck', '')}\n")
            f.write(f"- 机制: {e.get('mechanism', '')}\n")
            f.write(f"- 权衡: {e.get('trade_off', '')}\n")
            if e.get("evidence"):
                f.write(f"- 证据: {e.get('evidence', '')}\n")
            f.write("\n")

        bottlenecks = result.get("bottlenecks", [])
        if bottlenecks:
            f.write("## 瓶颈分析\n\n")
            for b in bottlenecks:
                f.write(f"### {b.get('description', '')}\n")
                f.write(f"- 受影响: {', '.join(b.get('affected_methods', []))}\n")
                f.write(f"- 已有尝试: {', '.join(b.get('attempts', []))}\n")
                f.write(f"- 残留差距: {b.get('remaining_gap', '')}\n")
                f.write(f"- 突破方向: {b.get('potential_direction', '')}\n\n")

        f.write("## 研究 Idea\n\n")
        for index, idea in enumerate(result.get("ideas", []), 1):
            f.write(f"### {index}. {idea.get('title', '')}\n\n")
            f.write(f"**动机:** {idea.get('motivation', '')}\n\n")
            f.write(f"**方法:** {idea.get('approach', '')}\n\n")
            f.write(f"**预期贡献:** {idea.get('expected_contribution', '')}\n\n")
            f.write(f"**相关方法:** {', '.join(idea.get('related_methods', []))}\n\n")
            f.write(
                f"**Gap 类型:** {idea.get('gap_type', '')} | "
                f"**新颖性:** {idea.get('novelty_score', '?')}/10 | "
                f"**可行性:** {idea.get('feasibility_score', '?')}/10\n\n"
            )
            if idea.get("novelty_rationale"):
                f.write(f"**Novelty Filter:** {idea.get('novelty_rationale', '')}\n\n")
            f.write("---\n\n")
    return path


def _run_pipeline(query: str, paper_count: int) -> Dict[str, Any]:
    progress = st.progress(0)
    status = st.empty()

    def update(message: str, pct: int) -> None:
        status.info(message)
        progress.progress(max(0, min(100, pct)))

    def on_search_progress(info: Dict[str, Any]) -> None:
        stage = info.get("stage")
        current = info.get("current", 0)
        total = max(info.get("total", 1), 1)
        pct = 12
        if stage == "recall":
            pct = 14
        elif stage == "verify":
            pct = 14 + int(12 * current / total)
        elif stage == "url":
            pct = 26 + int(14 * current / total)
        update(info.get("message") or "正在检索论文...", pct)

    update("正在召回并校验论文...", 8)
    papers = deepseek_search_papers(query, n=paper_count, progress_callback=on_search_progress)

    update("正在构建方法演化图谱...", 42)
    graph_data = deepseek_build_evolution(papers)
    methods = normalize_methods_list(graph_data.get("methods", []))
    edges = dedupe_edges(graph_data.get("evolution_edges", []))
    edges = dedupe_edges(enrich_edges_with_papers(papers, edges))
    bottlenecks = graph_data.get("bottlenecks", [])

    update("正在生成并重排研究 Idea...", 72)
    graph_context = {
        "query": query,
        "methods": methods,
        "evolution_edges": edges,
        "bottlenecks": bottlenecks,
    }
    ideas = generate_ideas(json.dumps(graph_context, ensure_ascii=False), max_ideas=max(MAX_IDEAS * 2, 6))
    ideas = annotate_and_rerank_ideas(ideas, methods, edges, max_ideas=MAX_IDEAS)

    update("正在保存报告...", 90)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_id = f"streamlit_{timestamp}"
    run_dir = os.path.join(OUTPUT_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    result = {
        "query": query,
        "run_id": run_id,
        "timestamp": timestamp,
        "papers": papers,
        "methods": methods,
        "evolution_edges": edges,
        "bottlenecks": bottlenecks,
        "ideas": ideas,
    }
    with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    report_path = _write_report(run_dir, result)
    result["report_path"] = report_path
    result["result_path"] = os.path.join(run_dir, "result.json")

    update("完成", 100)
    time.sleep(0.2)
    status.empty()
    return result


def _download_button(label: str, path: str, mime: str) -> None:
    if not path or not os.path.exists(path):
        return
    with open(path, "rb") as f:
        st.download_button(label, f, file_name=os.path.basename(path), mime=mime, use_container_width=True)


def _render_graph(methods: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
    if not methods and not edges:
        st.info("暂无可视化图谱数据。")
        return
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_path = os.path.join(tmpdir, "graph.html")
        generate_graph_html(methods, edges, graph_path)
        with open(graph_path, "r", encoding="utf-8") as f:
            components.html(f.read(), height=640, scrolling=True)


def _render_result(result: Dict[str, Any]) -> None:
    st.subheader("运行概览")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("论文", len(result.get("papers", [])))
    c2.metric("方法", len(result.get("methods", [])))
    c3.metric("演化边", len(result.get("evolution_edges", [])))
    c4.metric("Idea", len(result.get("ideas", [])))

    tab_papers, tab_methods, tab_edges, tab_ideas, tab_graph, tab_files = st.tabs(
        ["论文基础", "方法实体", "演化关系", "研究 Idea", "图谱", "导出"]
    )

    with tab_papers:
        papers = result.get("papers", [])
        if papers:
            st.dataframe(
                [
                    {
                        "year": p.get("year", ""),
                        "title": p.get("title", ""),
                        "key_method": p.get("key_method", ""),
                        "venue": p.get("venue", ""),
                        "citations": p.get("citations_approx", 0),
                        "source": p.get("verification_source", ""),
                        "url": p.get("url", ""),
                    }
                    for p in papers
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("暂无论文数据。")

    with tab_methods:
        methods = result.get("methods", [])
        if methods:
            st.dataframe(methods, use_container_width=True, hide_index=True)
        else:
            st.info("暂无方法实体。")

    with tab_edges:
        for edge in result.get("evolution_edges", []):
            title = f"{edge.get('source', '')} -> [{edge.get('relation', '')}] -> {edge.get('target', '')}"
            with st.expander(title):
                st.write(f"**瓶颈:** {edge.get('bottleneck', '')}")
                st.write(f"**机制:** {edge.get('mechanism', '')}")
                st.write(f"**权衡:** {edge.get('trade_off', '')}")
                if edge.get("evidence"):
                    st.write(f"**证据:** {edge.get('evidence', '')}")
        if not result.get("evolution_edges"):
            st.info("暂无演化关系。")

    with tab_ideas:
        for index, idea in enumerate(result.get("ideas", []), 1):
            st.markdown(f"### {index}. {idea.get('title', '')}")
            st.write(f"**动机:** {idea.get('motivation', '')}")
            st.write(f"**方法:** {idea.get('approach', '')}")
            st.write(f"**预期贡献:** {idea.get('expected_contribution', '')}")
            st.caption(
                f"Gap: {idea.get('gap_type', '')} | "
                f"新颖性 {idea.get('novelty_score', '?')}/10 | "
                f"可行性 {idea.get('feasibility_score', '?')}/10"
            )
            if idea.get("novelty_rationale"):
                st.caption(f"Novelty Filter: {idea.get('novelty_rationale', '')}")
            st.divider()
        if not result.get("ideas"):
            st.info("暂无研究 Idea。")

    with tab_graph:
        _render_graph(result.get("methods", []), result.get("evolution_edges", []))

    with tab_files:
        col_a, col_b = st.columns(2)
        with col_a:
            _download_button("下载 Markdown 报告", result.get("report_path", ""), "text/markdown")
        with col_b:
            _download_button("下载 JSON 数据", result.get("result_path", ""), "application/json")


def _load_history_run(run_id: str) -> Dict[str, Any] | None:
    data = get_run(run_id)
    if not data:
        return None
    run_dir = os.path.join(OUTPUT_DIR, run_id)
    data["run_id"] = run_id
    data["report_path"] = os.path.join(run_dir, "report.md")
    data["result_path"] = os.path.join(run_dir, "result.json")
    return data


st.title("🔬 IdeaLab")
st.caption("基于论文方法演化图谱的 AI 研究 Idea 生成器")

with st.sidebar:
    st.header("配置")
    key_ready = bool(os.environ.get("DEEPSEEK_API_KEY"))
    st.success("DeepSeek API Key 已配置") if key_ready else st.warning("请在 Streamlit secrets 中配置 DEEPSEEK_API_KEY")
    paper_count = st.slider("候选论文数", 8, 20, 15, 1)

    st.header("历史运行")
    runs = list_runs(limit=20)
    run_options = [""] + [run["id"] for run in runs]
    selected_run = st.selectbox("加载历史结果", run_options, format_func=lambda x: "选择历史记录" if not x else x)
    if selected_run and st.button("加载", use_container_width=True):
        loaded = _load_history_run(selected_run)
        if loaded:
            st.session_state["result"] = loaded
            st.rerun()

with st.form("run-form"):
    query = st.text_input(
        "研究方向",
        placeholder="例如: graph neural network for citation analysis",
    )
    submitted = st.form_submit_button("生成研究 Idea", use_container_width=True, disabled=not key_ready)

if submitted:
    if not query.strip():
        st.error("请输入研究方向。")
    else:
        try:
            st.session_state["result"] = _run_pipeline(query.strip(), paper_count)
            st.rerun()
        except Exception as exc:
            st.error(f"生成失败：{exc}")
            with st.expander("查看技术详情"):
                st.exception(exc)

if "result" in st.session_state:
    _render_result(st.session_state["result"])
else:
    st.info("输入研究方向后，系统会检索论文、构建方法演化图谱，并生成可执行研究 Idea。")

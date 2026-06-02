"""
IdeaLab Streamlit app.

This entrypoint is designed for Streamlit Community Cloud while reusing the
existing research pipeline modules.
"""
from __future__ import annotations

import json
import html
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="IdeaLab",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _bootstrap_secrets() -> None:
    """Expose Streamlit secrets as environment variables before local imports."""
    dotenv_values: Dict[str, str] = {}
    dotenv_path = Path(__file__).with_name(".env")
    if dotenv_path.exists():
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                dotenv_values[key.strip()] = value.strip().strip('"').strip("'")

    for key in ("DEEPSEEK_API_KEY", "S2_API_KEY"):
        if os.environ.get(key):
            continue
        if dotenv_values.get(key):
            os.environ[key] = dotenv_values[key]
            continue
        if key == "S2_API_KEY" and dotenv_path.exists():
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


def _inject_styles() -> None:
    """Tight Streamlit-specific polish for a denser research dashboard."""
    st.markdown(
        """
        <style>
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.22);
            padding-bottom: 0.3rem;
        }
        .stTabs [data-baseweb="tab"] {
            min-height: 2.85rem;
            padding: 0.65rem 1.05rem;
            border-radius: 0.45rem 0.45rem 0 0;
            font-size: 1.02rem;
            font-weight: 700;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(99, 102, 241, 0.16);
            border-bottom: 2px solid #818cf8;
        }
        .stButton > button,
        .stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] button {
            min-height: 2.85rem;
            font-weight: 700;
            border-radius: 0.45rem;
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 0.45rem;
            padding: 0.65rem 0.8rem;
            background: rgba(15, 23, 42, 0.32);
        }
        div[data-testid="stDataFrame"] div[role="toolbar"],
        div[data-testid="stDataFrame"] [data-testid*="Toolbar"],
        div[data-testid="stDataFrame"] [class*="toolbar"] {
            gap: 0.32rem !important;
            padding: 0.28rem !important;
            border-radius: 0.5rem !important;
            background: rgba(15, 23, 42, 0.78) !important;
            border: 1px solid rgba(148, 163, 184, 0.22) !important;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.24);
        }
        div[data-testid="stDataFrame"] div[role="toolbar"] button,
        div[data-testid="stDataFrame"] [data-testid*="Toolbar"] button,
        div[data-testid="stDataFrame"] [class*="toolbar"] button {
            width: 2.15rem !important;
            height: 2.15rem !important;
            min-width: 2.15rem !important;
            min-height: 2.15rem !important;
            border-radius: 0.42rem !important;
            color: #e2e8f0 !important;
            background: rgba(30, 41, 59, 0.72) !important;
            border: 1px solid rgba(148, 163, 184, 0.18) !important;
        }
        div[data-testid="stDataFrame"] div[role="toolbar"] button:hover,
        div[data-testid="stDataFrame"] [data-testid*="Toolbar"] button:hover,
        div[data-testid="stDataFrame"] [class*="toolbar"] button:hover {
            color: #ffffff !important;
            background: rgba(79, 70, 229, 0.4) !important;
            border-color: rgba(129, 140, 248, 0.55) !important;
        }
        div[data-testid="stDataFrame"] div[role="toolbar"] svg,
        div[data-testid="stDataFrame"] [data-testid*="Toolbar"] svg,
        div[data-testid="stDataFrame"] [class*="toolbar"] svg {
            width: 1.05rem !important;
            height: 1.05rem !important;
            stroke-width: 2.2px !important;
        }
        .idea-card {
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 0.5rem;
            padding: 1rem 1.1rem;
            margin: 0.85rem 0 1rem;
            background: rgba(15, 23, 42, 0.28);
        }
        .paper-card {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 0.5rem;
            padding: 0.95rem 1rem;
            margin: 0.75rem 0;
            background: rgba(2, 6, 23, 0.34);
        }
        .paper-title {
            font-size: 1rem;
            font-weight: 750;
            line-height: 1.35;
            margin-bottom: 0.45rem;
        }
        .paper-meta {
            color: #cbd5e1;
            font-size: 0.9rem;
            margin-bottom: 0.45rem;
        }
        .paper-abstract {
            color: #dbeafe;
            line-height: 1.55;
            margin-top: 0.55rem;
        }
        .idea-card h3 {
            margin-top: 0;
            margin-bottom: 0.5rem;
            font-size: 1.18rem;
            line-height: 1.35;
        }
        .idea-chip {
            display: inline-block;
            margin: 0 0.35rem 0.4rem 0;
            padding: 0.18rem 0.5rem;
            border: 1px solid rgba(129, 140, 248, 0.42);
            border-radius: 999px;
            color: #c7d2fe;
            font-size: 0.82rem;
        }
        .paper-chip {
            display: inline-block;
            margin: 0 0.32rem 0.36rem 0;
            padding: 0.16rem 0.46rem;
            border: 1px solid rgba(56, 189, 248, 0.36);
            border-radius: 999px;
            color: #bae6fd;
            font-size: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_inject_styles()


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(str(item) for item in value if item)
    if value is None:
        return ""
    return str(value)


def _html(value: Any) -> str:
    return html.escape(_as_text(value), quote=True)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
            f.write(f"**局限性:** {_as_text(idea.get('limitations')) or '未生成'}\n\n")
            f.write(f"**主要风险:** {_as_text(idea.get('risks')) or '未生成'}\n\n")
            f.write(f"**验证方案:** {_as_text(idea.get('validation_plan')) or '未生成'}\n\n")
            if idea.get("required_resources"):
                f.write(f"**资源需求:** {_as_text(idea.get('required_resources'))}\n\n")
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


def _run_pipeline(query: str, paper_count: int, fill_missing_urls: bool) -> Dict[str, Any]:
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
        elif stage == "url_skipped":
            pct = 40
        update(info.get("message") or "正在检索论文...", pct)

    update("正在召回并校验论文...", 8)
    try:
        papers = deepseek_search_papers(
            query,
            n=paper_count,
            progress_callback=on_search_progress,
            fill_missing_urls=fill_missing_urls,
        )
    except TypeError as exc:
        if "fill_missing_urls" not in str(exc):
            raise
        update("当前运行环境仍在使用旧版检索函数，已自动回退兼容模式...", 10)
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


def _paper_table_rows(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for index, paper in enumerate(papers, 1):
        rows.append(
            {
                "#": index,
                "year": _as_int(paper.get("year"), 0),
                "title": paper.get("title", ""),
                "method": paper.get("key_method", ""),
                "venue": paper.get("venue", ""),
                "citations": _as_int(paper.get("citations_approx"), 0),
                "source": paper.get("verification_source", "") or "unknown",
                "link": paper.get("url", ""),
            }
        )
    return rows


def _render_papers_tab(papers: List[Dict[str, Any]]) -> None:
    if not papers:
        st.info("暂无论文数据。")
        return

    sources = sorted({(paper.get("verification_source") or "unknown") for paper in papers})
    col_filter, col_source, col_sort = st.columns([2.3, 1.15, 1.2])
    keyword = col_filter.text_input("筛选论文", placeholder="标题、方法、venue 或摘要关键词")
    source_choice = col_source.selectbox("来源", ["全部"] + sources)
    sort_choice = col_sort.selectbox("排序", ["召回顺序", "年份新到旧", "年份旧到新", "引用数高到低"])

    filtered = []
    keyword_norm = keyword.strip().lower()
    for paper in papers:
        if source_choice != "全部" and (paper.get("verification_source") or "unknown") != source_choice:
            continue
        haystack = " ".join(
            str(paper.get(field, ""))
            for field in ["title", "key_method", "venue", "abstract", "authors"]
        ).lower()
        if keyword_norm and keyword_norm not in haystack:
            continue
        filtered.append(paper)

    if sort_choice == "年份新到旧":
        filtered.sort(key=lambda item: _as_int(item.get("year"), 0), reverse=True)
    elif sort_choice == "年份旧到新":
        filtered.sort(key=lambda item: _as_int(item.get("year"), 0))
    elif sort_choice == "引用数高到低":
        filtered.sort(key=lambda item: _as_int(item.get("citations_approx"), 0), reverse=True)

    st.caption(f"显示 {len(filtered)} / {len(papers)} 篇论文")
    st.dataframe(
        _paper_table_rows(filtered),
        use_container_width=True,
        hide_index=True,
        height=min(520, 92 + max(len(filtered), 1) * 36),
        column_order=["#", "year", "title", "method", "venue", "citations", "source", "link"],
        column_config={
            "#": st.column_config.NumberColumn("#", width="small"),
            "year": st.column_config.NumberColumn("年份", width="small"),
            "title": st.column_config.TextColumn("论文标题", width="large"),
            "method": st.column_config.TextColumn("核心方法", width="medium"),
            "venue": st.column_config.TextColumn("Venue", width="small"),
            "citations": st.column_config.NumberColumn("引用", width="small"),
            "source": st.column_config.TextColumn("校验来源", width="small"),
            "link": st.column_config.LinkColumn("链接", display_text="打开", width="small"),
        },
    )

    st.markdown("#### 论文摘要与证据")
    for index, paper in enumerate(filtered, 1):
        title = paper.get("title", "") or "Untitled paper"
        with st.expander(f"{index}. [{paper.get('year', '?')}] {title}"):
            url = paper.get("url", "")
            link_html = f'<a href="{_html(url)}" target="_blank">打开论文链接</a>' if url else "暂无链接"
            st.markdown(
                f"""
                <div class="paper-card">
                    <div class="paper-title">{_html(title)}</div>
                    <div class="paper-meta">
                        {_html(paper.get('authors') or '作者未知')} ·
                        {_html(paper.get('venue') or 'Venue 未知')} ·
                        引用 {_html(paper.get('citations_approx', 0))}
                    </div>
                    <span class="paper-chip">方法：{_html(paper.get('key_method') or '未标注')}</span>
                    <span class="paper-chip">来源：{_html(paper.get('verification_source') or 'unknown')}</span>
                    <span class="paper-chip">{link_html}</span>
                    <div class="paper-abstract">{_html(paper.get('abstract') or '暂无摘要。')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


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
        _render_papers_tab(papers)

    with tab_methods:
        methods = result.get("methods", [])
        if methods:
            st.dataframe(
                methods,
                use_container_width=True,
                hide_index=True,
                height=min(520, 90 + max(len(methods), 1) * 38),
                column_config={
                    "name": st.column_config.TextColumn("方法", width="medium"),
                    "canonical_name": st.column_config.TextColumn("标准名", width="medium"),
                    "category": st.column_config.TextColumn("类别", width="small"),
                    "description": st.column_config.TextColumn("描述", width="large"),
                    "first_paper": st.column_config.TextColumn("首次论文", width="large"),
                    "year": st.column_config.NumberColumn("年份", width="small"),
                },
            )
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
            related_chips = "".join(
                f'<span class="idea-chip">{_html(method)}</span>'
                for method in idea.get("related_methods", [])
            )
            st.markdown(
                f"""
                <div class="idea-card">
                    <h3>{index}. {_html(idea.get('title', ''))}</h3>
                    <div>
                        <span class="idea-chip">Gap: {_html(idea.get('gap_type', ''))}</span>
                        <span class="idea-chip">新颖性 {_html(idea.get('novelty_score', '?'))}/10</span>
                        <span class="idea-chip">可行性 {_html(idea.get('feasibility_score', '?'))}/10</span>
                    </div>
                    <p><strong>动机：</strong>{_html(idea.get('motivation', ''))}</p>
                    <p><strong>方法：</strong>{_html(idea.get('approach', ''))}</p>
                    <p><strong>预期贡献：</strong>{_html(idea.get('expected_contribution', ''))}</p>
                    <p><strong>局限性：</strong>{_html(idea.get('limitations') or '未生成')}</p>
                    <p><strong>主要风险：</strong>{_html(idea.get('risks') or '未生成')}</p>
                    <p><strong>验证方案：</strong>{_html(idea.get('validation_plan') or '未生成')}</p>
                    <p><strong>资源需求：</strong>{_html(idea.get('required_resources') or '未生成')}</p>
                    <p><strong>相关方法：</strong>{related_chips or '未生成'}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if idea.get("novelty_rationale"):
                st.caption(f"Novelty Filter: {idea.get('novelty_rationale', '')}")
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
    if key_ready:
        st.success("DeepSeek API Key 已配置")
    else:
        st.warning("请在 Streamlit secrets 中配置 DEEPSEEK_API_KEY")
    paper_count = st.slider("候选论文数", 6, 50, 18, 1)
    speed_first = st.checkbox(
        "速度优先：跳过二次链接补全",
        value=True,
        help="保留论文校验，但跳过额外 URL 查询，通常能更快出结果。",
    )

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
            st.session_state["result"] = _run_pipeline(query.strip(), paper_count, fill_missing_urls=not speed_first)
            st.rerun()
        except Exception as exc:
            st.error(f"生成失败：{exc}")
            with st.expander("查看技术详情"):
                st.exception(exc)

if "result" in st.session_state:
    _render_result(st.session_state["result"])
else:
    st.info("输入研究方向后，系统会检索论文、构建方法演化图谱，并生成可执行研究 Idea。")

"""
IdeaLab Web Server — v2 with visualization & history
"""
import sys, os, json, threading, uuid, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_from_directory
from fast import deepseek_search_papers, deepseek_build_evolution, _fill_urls
from analyzer import generate_ideas
from visualizer import generate_graph_html
from history import list_runs, get_run, delete_run, compare_runs
from config import OUTPUT_DIR, MAX_IDEAS

app = Flask(__name__, template_folder="templates", static_folder="static")

jobs = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def start_run():
    data = request.json
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "请输入研究方向"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "query": query,
        "status": "running",
        "step": "初始化...",
        "progress": 0,
        "result": None,
        "error": None,
    }

    thread = threading.Thread(target=run_pipeline, args=(job_id, query))
    thread.daemon = True
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(job)


@app.route("/api/history")
def api_history():
    limit = request.args.get("limit", 20, type=int)
    return jsonify(list_runs(limit))


@app.route("/api/history/<run_id>")
def api_run_detail(run_id):
    data = get_run(run_id)
    if not data:
        return jsonify({"error": "未找到"}), 404
    return jsonify(data)


@app.route("/api/history/<run_id>", methods=["DELETE"])
def api_delete_run(run_id):
    ok = delete_run(run_id)
    return jsonify({"success": ok})


@app.route("/api/compare", methods=["POST"])
def api_compare():
    ids = request.json.get("ids", [])
    return jsonify(compare_runs(ids))


@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)


def run_pipeline(job_id, query):
    job = jobs[job_id]
    try:
        # Step 1: 搜索论文
        job["step"] = "正在搜索论文..."
        job["progress"] = 10
        papers = deepseek_search_papers(query, n=15)
        print(f"  搜索到 {len(papers)} 篇论文")

        # 补充链接
        job["step"] = "正在查找论文链接..."
        job["progress"] = 20
        papers = _fill_urls(papers)

        job["papers"] = papers
        job["progress"] = 30
        job["step"] = f"找到 {len(papers)} 篇论文，正在构建演化图..."

        # Step 2: 构建演化图
        time.sleep(0.3)
        graph_data = deepseek_build_evolution(papers)
        methods = graph_data.get("methods", [])
        edges = graph_data.get("evolution_edges", [])
        bottlenecks = graph_data.get("bottlenecks", [])
        job["progress"] = 60
        job["step"] = f"发现 {len(methods)} 个方法、{len(edges)} 条演化边，正在生成 Idea..."

        # Step 3: 生成 Idea
        time.sleep(0.3)
        context = f"""研究方向: {query}
方法演化图: {json.dumps(graph_data, ensure_ascii=False)}
请生成 {MAX_IDEAS} 个创新研究 idea。"""
        ideas = generate_ideas(context, max_ideas=MAX_IDEAS)
        job["progress"] = 80
        job["step"] = "正在生成可视化图谱..."

        # Step 4: 保存结果
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        run_id = f"web_{timestamp}"
        run_dir = os.path.join(OUTPUT_DIR, run_id)
        os.makedirs(run_dir, exist_ok=True)

        result = {
            "query": query,
            "run_id": run_id,
            "papers": papers,
            "methods": methods,
            "evolution_edges": edges,
            "bottlenecks": bottlenecks,
            "ideas": ideas,
        }

        # 保存 JSON
        with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 生成可视化图谱
        graph_path = os.path.join(run_dir, "graph.html")
        generate_graph_html(methods, edges, graph_path)
        result["graph_url"] = f"/output/{run_id}/graph.html"

        # 生成 Markdown 报告
        _write_report(run_dir, result)

        job["progress"] = 95
        job["step"] = "正在生成报告..."

        job["result"] = result
        job["progress"] = 100
        job["status"] = "done"
        job["step"] = "完成！"

    except Exception as e:
        import traceback
        traceback.print_exc()
        job["status"] = "error"
        job["error"] = str(e)
        job["step"] = f"出错: {e}"


def _write_report(run_dir, result):
    """生成 Markdown 报告"""
    papers = result.get("papers", [])
    methods = result.get("methods", [])
    edges = result.get("evolution_edges", [])
    bottlenecks = result.get("bottlenecks", [])
    ideas = result.get("ideas", [])
    query = result.get("query", "")

    path = os.path.join(run_dir, "report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# IdeaLab 研究报告\n\n**查询:** {query}\n\n")

        f.write("## 论文基础\n\n")
        for p in papers:
            link = p.get("url", "")
            if link:
                f.write(f"- [{p.get('year','?')}] **[{p.get('title','')}]({link})** — {p.get('key_method','')}\n")
            else:
                f.write(f"- [{p.get('year','?')}] **{p.get('title','')}** — {p.get('key_method','')}\n")
            f.write(f"  > {p.get('abstract','')}\n\n")

        f.write("## 方法列表\n\n")
        for m in methods:
            f.write(f"- **{m.get('name','')}** ({m.get('category','')}, {m.get('year','')}): {m.get('description','')}\n")

        f.write("\n## 方法演化图\n\n```\n")
        targets = set(e.get("target","") for e in edges)
        sources = set(e.get("source","") for e in edges)
        roots = sources - targets
        for root in roots:
            f.write(f"{root}\n")
            children = [e for e in edges if e.get("source") == root]
            for i, e in enumerate(children):
                prefix = "└──" if i == len(children)-1 else "├──"
                f.write(f"  {prefix}→ [{e.get('relation','')}] {e.get('target','')}\n")
        f.write("```\n\n")

        f.write("## 演化关系\n\n")
        for e in edges:
            f.write(f"### {e.get('source','')} →[{e.get('relation','')}]→ {e.get('target','')}\n")
            f.write(f"- 瓶颈: {e.get('bottleneck','')}\n")
            f.write(f"- 机制: {e.get('mechanism','')}\n")
            f.write(f"- 权衡: {e.get('trade_off','')}\n\n")

        if bottlenecks:
            f.write("## 瓶颈分析\n\n")
            for b in bottlenecks:
                f.write(f"### {b.get('description','')}\n")
                f.write(f"- 受影响: {', '.join(b.get('affected_methods',[]))}\n")
                f.write(f"- 突破方向: {b.get('potential_direction','')}\n\n")

        f.write("## 研究 Idea\n\n")
        for i, idea in enumerate(ideas, 1):
            f.write(f"### {i}. {idea.get('title','')}\n\n")
            f.write(f"**动机:** {idea.get('motivation','')}\n\n")
            f.write(f"**方法:** {idea.get('approach','')}\n\n")
            f.write(f"**预期贡献:** {idea.get('expected_contribution','')}\n\n")
            f.write(f"**相关方法:** {', '.join(idea.get('related_methods',[]))}\n\n")
            f.write(f"**新颖性:** {idea.get('novelty_score','?')}/10 | **可行性:** {idea.get('feasibility_score','?')}/10\n\n---\n\n")


if __name__ == "__main__":
    print("🔬 IdeaLab Web Server v2")
    print("   打开浏览器访问: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)

"""
历史记录管理 — 查看、对比、删除历史运行结果
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OUTPUT_DIR


def list_runs(limit: int = 20) -> list:
    """列出所有历史运行"""
    runs = []
    pattern = os.path.join(OUTPUT_DIR, "*")
    for d in sorted(glob.glob(pattern), reverse=True):
        if not os.path.isdir(d):
            continue
        result_file = os.path.join(d, "result.json")
        if os.path.exists(result_file):
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                runs.append({
                    "id": os.path.basename(d),
                    "path": d,
                    "query": data.get("query", ""),
                    "timestamp": data.get("timestamp", ""),
                    "num_papers": len(data.get("papers", [])),
                    "num_methods": len(data.get("methods", [])),
                    "num_edges": len(data.get("evolution_edges", [])),
                    "num_ideas": len(data.get("ideas", [])),
                    "has_graph": os.path.exists(os.path.join(d, "graph.html")),
                })
            except Exception:
                pass
        if len(runs) >= limit:
            break
    return runs


def get_run(run_id: str) -> dict:
    """获取单次运行详情"""
    run_dir = os.path.join(OUTPUT_DIR, run_id)
    result_file = os.path.join(run_dir, "result.json")
    if os.path.exists(result_file):
        with open(result_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def get_report_path(run_id: str) -> str:
    """获取报告文件路径"""
    path = os.path.join(OUTPUT_DIR, run_id, "report.md")
    return path if os.path.exists(path) else None


def get_graph_path(run_id: str) -> str:
    """获取图谱文件路径"""
    path = os.path.join(OUTPUT_DIR, run_id, "graph.html")
    return path if os.path.exists(path) else None


def delete_run(run_id: str) -> bool:
    """删除某次运行"""
    import shutil
    run_dir = os.path.join(OUTPUT_DIR, run_id)
    if os.path.exists(run_dir):
        shutil.rmtree(run_dir)
        return True
    return False


def compare_runs(run_ids: list) -> dict:
    """对比多次运行的结果"""
    comparison = []
    for rid in run_ids:
        data = get_run(rid)
        if data:
            comparison.append({
                "id": rid,
                "query": data.get("query", ""),
                "num_methods": len(data.get("methods", [])),
                "num_edges": len(data.get("evolution_edges", [])),
                "ideas": [
                    {
                        "title": i.get("title", ""),
                        "novelty": i.get("novelty_score", 0),
                        "feasibility": i.get("feasibility_score", 0),
                    }
                    for i in data.get("ideas", [])
                ],
            })
    return {"runs": comparison}

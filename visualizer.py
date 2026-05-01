"""
方法演化图可视化 — 用 pyvis 生成交互式图谱
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from pyvis.network import Network
    HAS_PYVIS = True
except ImportError:
    HAS_PYVIS = False


# 方法类别配色
CATEGORY_COLORS = {
    "architecture": "#6c5ce7",
    "training": "#00b894",
    "optimization": "#e17055",
    "data": "#fdcb6e",
    "evaluation": "#74b9ff",
    "pretraining": "#a29bfe",
    "training_method": "#00b894",
    "unknown": "#636e72",
}

# 演化关系配色
RELATION_COLORS = {
    "extends": "#6c5ce7",
    "improves": "#00b894",
    "replaces": "#e74c3c",
    "adapts": "#fdcb6e",
    "uses_component": "#74b9ff",
}


def generate_graph_html(methods: list, edges: list, output_path: str) -> str:
    """生成交互式 HTML 图谱"""
    if not HAS_PYVIS:
        # fallback: 生成纯 HTML/SVG
        return _generate_svg_graph(methods, edges, output_path)

    net = Network(
        height="600px",
        width="100%",
        directed=True,
        bgcolor="#0a0a0a",
        font_color="#e0e0e0",
        notebook=False,
    )

    net.barnes_hut(
        gravity=-3000,
        central_gravity=0.3,
        spring_length=200,
        spring_strength=0.05,
    )

    # 添加节点
    for m in methods:
        name = m.get("name", "unknown")
        cat = m.get("category", "unknown")
        color = CATEGORY_COLORS.get(cat, "#636e72")
        label = name
        title = f"""
        <b>{name}</b><br>
        类别: {cat}<br>
        描述: {m.get('description', '')}<br>
        年份: {m.get('year', '?')}
        """
        net.add_node(name, label=label, color=color, title=title, size=25)

    # 添加边
    for e in edges:
        src = e.get("source", "")
        tgt = e.get("target", "")
        rel = e.get("relation", "")
        color = RELATION_COLORS.get(rel, "#636e72")
        title = f"""
        <b>{src} → {tgt}</b><br>
        关系: {rel}<br>
        瓶颈: {e.get('bottleneck', '')}<br>
        机制: {e.get('mechanism', '')}
        """
        net.add_edge(src, tgt, color=color, title=title, width=2, arrows="to")

    # 生成 HTML
    html = net.generate_html()

    # 注入自定义样式 + 图例
    custom_style = """
    <style>
    body { background: #0a0a0a !important; margin: 0; padding: 0; }
    #mynetwork { border-radius: 12px; border: 1px solid #222; }
    .legend { position: fixed; bottom: 16px; left: 16px; background: rgba(17,17,24,0.95); border: 1px solid #333; border-radius: 10px; padding: 14px 18px; z-index: 999; font-family: -apple-system, sans-serif; font-size: 12px; color: #ccc; backdrop-filter: blur(8px); }
    .legend h4 { color: #fff; font-size: 13px; margin: 0 0 10px 0; }
    .legend-section { margin-bottom: 10px; }
    .legend-section:last-child { margin-bottom: 0; }
    .legend-section .title { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .legend-item { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
    .legend-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
    .legend-line { width: 20px; height: 3px; border-radius: 2px; flex-shrink: 0; }
    </style>
    """
    legend_html = """
    <div class="legend">
      <h4>📊 图谱说明</h4>
      <div class="legend-section">
        <div class="title">节点 = 方法类别</div>
        <div class="legend-item"><span class="legend-dot" style="background:#6c5ce7"></span> architecture (架构)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#00b894"></span> training (训练)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#e17055"></span> optimization (优化)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#fdcb6e"></span> data (数据)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#74b9ff"></span> evaluation (评估)</div>
        <div class="legend-item"><span class="legend-dot" style="background:#a29bfe"></span> pretraining (预训练)</div>
      </div>
      <div class="legend-section">
        <div class="title">连线 = 演化关系</div>
        <div class="legend-item"><span class="legend-line" style="background:#6c5ce7"></span> extends (扩展)</div>
        <div class="legend-item"><span class="legend-line" style="background:#00b894"></span> improves (改进)</div>
        <div class="legend-item"><span class="legend-line" style="background:#e74c3c"></span> replaces (替代)</div>
        <div class="legend-item"><span class="legend-line" style="background:#fdcb6e"></span> adapts (适配)</div>
        <div class="legend-item"><span class="legend-line" style="background:#74b9ff"></span> uses_component (组合)</div>
      </div>
      <div style="color:#555;font-size:10px;margin-top:8px">💡 悬停节点/连线查看详情 · 拖拽移动 · 滚轮缩放</div>
    </div>
    """
    html = html.replace("<head>", f"<head>{custom_style}")
    html = html.replace("</body>", f"{legend_html}</body>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def _generate_svg_graph(methods: list, edges: list, output_path: str) -> str:
    """不依赖 pyvis 的纯 HTML/SVG 图谱"""
    # 计算布局 (简单力导向)
    import math, random
    random.seed(42)

    nodes = {}
    for i, m in enumerate(methods):
        name = m.get("name", f"method_{i}")
        angle = 2 * math.pi * i / max(len(methods), 1)
        r = 200
        nodes[name] = {
            "x": 400 + r * math.cos(angle),
            "y": 300 + r * math.sin(angle),
            "cat": m.get("category", "unknown"),
            "desc": m.get("description", ""),
            "year": m.get("year", "?"),
        }

    # SVG 生成
    svg_parts = ['<svg viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">']
    svg_parts.append('<rect width="800" height="600" fill="#0a0a0a"/>')

    # 绘制边
    for e in edges:
        src = nodes.get(e.get("source"))
        tgt = nodes.get(e.get("target"))
        if src and tgt:
            color = RELATION_COLORS.get(e.get("relation", ""), "#636e72")
            svg_parts.append(f'<line x1="{src["x"]}" y1="{src["y"]}" x2="{tgt["x"]}" y2="{tgt["y"]}" stroke="{color}" stroke-width="2" marker-end="url(#arrow)"/>')

    # 箭头定义
    svg_parts.insert(1, '''<defs><marker id="arrow" viewBox="0 0 10 10" refX="25" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#636e72"/></marker></defs>''')

    # 绘制节点
    for name, info in nodes.items():
        color = CATEGORY_COLORS.get(info["cat"], "#636e72")
        x, y = info["x"], info["y"]
        svg_parts.append(f'<circle cx="{x}" cy="{y}" r="20" fill="{color}" stroke="#222" stroke-width="2"/>')
        svg_parts.append(f'<text x="{x}" y="{y+35}" text-anchor="middle" fill="#e0e0e0" font-size="11" font-family="sans-serif">{name}</text>')

    svg_parts.append('</svg>')

    legend = """
    <div style="position:fixed;bottom:16px;left:16px;background:rgba(17,17,24,0.95);border:1px solid #333;border-radius:10px;padding:14px 18px;font-family:-apple-system,sans-serif;font-size:12px;color:#ccc">
      <div style="color:#fff;font-size:13px;margin-bottom:10px">📊 图谱说明</div>
      <div style="margin-bottom:8px;color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px">节点 = 方法类别</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:12px;height:12px;border-radius:50%;background:#6c5ce7;display:inline-block"></span> architecture (架构)</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:12px;height:12px;border-radius:50%;background:#00b894;display:inline-block"></span> training (训练)</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:12px;height:12px;border-radius:50%;background:#e17055;display:inline-block"></span> optimization (优化)</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:12px;height:12px;border-radius:50%;background:#fdcb6e;display:inline-block"></span> data (数据)</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:12px;height:12px;border-radius:50%;background:#74b9ff;display:inline-block"></span> evaluation (评估)</div>
      <div style="margin-top:8px;color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px">连线 = 演化关系</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:20px;height:3px;border-radius:2px;background:#6c5ce7;display:inline-block"></span> extends (扩展)</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:20px;height:3px;border-radius:2px;background:#00b894;display:inline-block"></span> improves (改进)</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:20px;height:3px;border-radius:2px;background:#e74c3c;display:inline-block"></span> replaces (替代)</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:20px;height:3px;border-radius:2px;background:#fdcb6e;display:inline-block"></span> adapts (适配)</div>
      <div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:20px;height:3px;border-radius:2px;background:#74b9ff;display:inline-block"></span> uses_component (组合)</div>
    </div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>IdeaLab 方法演化图</title>
<style>
body {{ background: #0a0a0a; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
svg {{ max-width: 100%; height: auto; border-radius: 12px; border: 1px solid #222; }}
</style></head>
<body>{"".join(svg_parts)}{legend}</body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path

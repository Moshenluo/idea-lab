"""
DeepSeek LLM 分析器 — 方法提取 + 演化关系识别 + Idea 生成
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def _client():
    if not DEEPSEEK_API_KEY:
        raise ValueError(
            "未设置 DEEPSEEK_API_KEY！\n"
            "请运行: $env:DEEPSEEK_API_KEY = 'your-key-here'\n"
            "或在 config.py 中直接填写"
        )
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def _chat(system: str, user: str, temperature: float = 0.3) -> str:
    client = _client()
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return resp.choices[0].message.content


def _parse_json(text: str) -> dict | list:
    """从 LLM 输出中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试提取 ```json ... ``` 块
    import re
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 尝试找第一个 { 或 [
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
    raise ValueError(f"无法从 LLM 输出中提取 JSON:\n{text[:500]}")


# ─── 方法提取 ─────────────────────────────────────────────

EXTRACT_METHODS_PROMPT = """你是一个 AI 研究方法分析专家。
从给定的论文信息中，提取核心方法/技术。

输出 JSON 数组，每个元素:
{
  "name": "方法名 (如 Transformer, BERT, GNN)",
  "description": "一句话描述",
  "category": "类别 (如 architecture, training_method, loss_function, data_augmentation, optimization)",
  "novelty": "new | improvement | application"
}

规则:
- 只提取论文核心贡献的方法，不要提及其引用的旧方法
- 方法名用领域通用名称
- 每篇论文通常 1-3 个方法"""


def extract_methods(paper_summary: str) -> list:
    """从论文摘要中提取方法"""
    resp = _chat(EXTRACT_METHODS_PROMPT, f"论文信息:\n{paper_summary}")
    try:
        return _parse_json(resp)
    except ValueError:
        return []


# ─── 演化关系识别 ─────────────────────────────────────────

EVOLUTION_PROMPT = """你是一个 AI 方法演化分析专家。
给定两篇论文的信息（论文 A 引用了论文 B），判断它们之间的方法演化关系。

输出 JSON:
{
  "relation": "extends | improves | replaces | adapts | uses_component | compares | unrelated",
  "bottleneck": "论文 B 的方法有什么瓶颈/局限？论文 A 如何解决？",
  "mechanism": "论文 A 用了什么具体机制来改进？",
  "trade_off": "改进带来了什么权衡？",
  "confidence": 0.0-1.0
}

关系类型说明:
- extends: 在 B 的框架上扩展新能力
- improves: 直接提升 B 的性能指标
- replaces: 用全新方法替代 B
- adapts: 将 B 适配到新领域/场景
- uses_component: 使用 B 作为模块
- compares: 仅实验对比，无方法继承
- unrelated: 无实质方法关系"""


def analyze_evolution(paper_a_summary: str, paper_b_summary: str) -> dict:
    """分析两篇论文间的方法演化关系"""
    user_msg = f"""论文 A (引用方):
{paper_a_summary}

论文 B (被引用方):
{paper_b_summary}

请分析 A 对 B 的方法演化关系。"""
    resp = _chat(EVOLUTION_PROMPT, user_msg)
    try:
        return _parse_json(resp)
    except ValueError:
        return {"relation": "unrelated", "confidence": 0}


# ─── Idea 生成 ────────────────────────────────────────────

IDEA_PROMPT = """你是一个 AI 研究创意专家。
基于给定的方法演化图谱信息，生成创新的研究 idea。

你需要:
1. 分析图谱中的方法演化脉络
2. 找出未被探索的空白区域或未解决的瓶颈
3. 生成可执行的研究提案

输出 JSON 数组 (最多 5 个):
[{
  "title": "研究 idea 标题",
  "motivation": "为什么这个方向值得探索 (基于图谱中的哪个瓶颈/空白)",
  "approach": "拟采用的方法 (简要技术路线)",
  "expected_contribution": "预期贡献",
  "related_methods": ["涉及的方法名"],
  "gap_type": "bottleneck_resolution | trend_extrapolation | cross_pollination | paradigm_challenge",
  "novelty_score": 1-10,
  "feasibility_score": 1-10
}]"""


def generate_ideas(graph_context: str, max_ideas: int = 5) -> list:
    """基于图谱上下文生成研究 idea"""
    user_msg = f"""以下是方法演化图谱的结构化信息:

{graph_context}

请基于这些信息生成 {max_ideas} 个创新的研究 idea。重点关注:
1. 被反复提及但未解决的瓶颈
2. 有明显演化趋势但尚未到达的方向
3. 两个方法线之间缺失的桥梁
4. 被主流忽视但有潜力的替代路径"""
    resp = _chat(IDEA_PROMPT, user_msg, temperature=0.7)
    try:
        return _parse_json(resp)
    except ValueError:
        return []


# ─── 瓶颈分析 ────────────────────────────────────────────

BOTTLENECK_PROMPT = """分析以下方法演化路径中的关键瓶颈。

输出 JSON:
{
  "bottlenecks": [
    {
      "description": "瓶颈描述",
      "affected_methods": ["受影响的方法"],
      "attempts": ["已有的解决尝试"],
      "remaining_gap": "仍然存在的差距",
      "potential_direction": "可能的突破方向"
    }
  ]
}"""


def analyze_bottlenecks(evolution_chains: str) -> dict:
    """分析演化链中的瓶颈"""
    resp = _chat(BOTTLENECK_PROMPT, f"方法演化链:\n{evolution_chains}")
    try:
        return _parse_json(resp)
    except ValueError:
        return {"bottlenecks": []}

# 🔬 IdeaLab — AI Research Idea Generator

基于方法演化图谱的 AI 研究 Idea 生成器。输入研究方向，自动搜索论文、构建方法演化图谱、分析瓶颈、生成研究 Idea。

灵感来自 [Intern-Atlas (书生·通鉴)](https://arxiv.org/abs/2604.28158) 的方法论演化图谱思路。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能

- 🔍 **智能论文搜索** — 基于研究方向自动检索 15 篇核心论文
- 🧠 **方法实体提取** — LLM 自动识别论文中的核心方法/技术
- 🔗 **演化关系识别** — 分析方法间的 extends/improves/replaces/adapts 关系
- ⚠️ **瓶颈分析** — 识别方法演化中的关键瓶颈和未解决问题
- 💡 **Idea 生成** — 基于图谱空白区域生成创新研究提案
- 🌐 **Web 界面** — 一键启动，浏览器可视化操作

## 📸 界面预览

```
┌─────────────────────────────────────────┐
│  🔬 IdeaLab                             │
│  基于方法演化图谱的 AI 研究 Idea 生成器   │
├─────────────────────────────────────────┤
│  ┌─────────────────────────┐ [🚀 生成]  │
│  │ 输入研究方向...          │            │
│  └─────────────────────────┘            │
│  ████████████████░░░░░░░░ 60%           │
│  正在构建演化图...                        │
├─────────────────────────────────────────┤
│  📄 论文基础 (15篇)                      │
│  🔧 方法实体 (9个)                       │
│  🔗 演化关系 (8条)                       │
│  ⚠️ 瓶颈分析 (5个)                      │
│  💡 研究 Idea (5个)                      │
└─────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install flask networkx requests openai
```

### 2. 设置 API Key

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY = "sk-your-key-here"

# Linux/macOS
export DEEPSEEK_API_KEY="sk-your-key-here"
```

### 3. 启动 Web 界面

```bash
python server.py
```

然后打开浏览器访问 **http://localhost:5000**

### 4. 或者用命令行

```bash
# 快速模式（推荐，纯 DeepSeek 驱动）
python fast.py "graph neural network for citation analysis"

# 完整模式（需要 Semantic Scholar API key）
python main.py "your research topic"
```

## 📁 项目结构

```
idea-lab/
├── server.py          # Web 服务器 (Flask)
├── templates/
│   └── index.html     # 前端界面
├── fast.py            # 快速模式 pipeline（纯 LLM）
├── main.py            # 完整模式 pipeline（LLM + S2 API）
├── analyzer.py        # DeepSeek LLM 分析器
├── graph_builder.py   # 引用图构建 (NetworkX)
├── scholar.py         # Semantic Scholar API 封装
├── config.py          # 配置文件
├── demo.py            # 模拟数据 demo
└── output/            # 运行结果
```

## 🔧 配置说明

在 `config.py` 中可以调整：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | 环境变量 | DeepSeek API key |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 使用的模型 |
| `MAX_IDEAS` | 5 | 生成 idea 数量 |
| `YEAR_RANGE` | (2020, 2025) | 论文年份范围 |

## 📊 费用估算

| 模式 | 调用次数 | 费用 |
|------|---------|------|
| Fast 模式 | ~6 次 DeepSeek | ≈ ¥0.02 |
| 完整模式 | ~50 次 DeepSeek + S2 API | ≈ ¥0.1-0.3 |

## 🧠 工作原理

```
研究方向 → LLM 搜索论文 → LLM 提取方法 → LLM 识别演化关系
                                                    ↓
                              瓶颈分析 ← 方法演化图谱 (NetworkX)
                                  ↓
                              Idea 生成 → 研究报告 (Markdown + JSON)
```

核心思路来自 Intern-Atlas：
- **方法作为原子单位**（而非论文）
- **语义化边类型**（extends/improves/replaces/adapts）
- **瓶颈-机制-权衡**三元组记录每条演化边
- **基于图谱空白**生成 idea（而非自由联想）

## 📝 输出示例

每次运行生成：
- `result.json` — 结构化数据（论文、方法、演化边、idea）
- `report.md` — 可读 Markdown 报告

Idea 包含：
- 标题、动机、方法、预期贡献
- 相关方法、Gap 类型
- 新颖性评分 (1-10)、可行性评分 (1-10)

## 🙏 致谢

- [Intern-Atlas](https://arxiv.org/abs/2604.28158) — 方法论演化图谱的理论基础
- [Semantic Scholar](https://www.semanticscholar.org/) — 学术论文 API
- [DeepSeek](https://platform.deepseek.com/) — LLM 推理

## 📄 License

MIT

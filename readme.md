# 🔬 IdeaLab — AI Research Idea Generator

基于方法演化图谱的 AI 研究 Idea 生成器。输入研究方向，自动搜索论文、提取方法、构建演化图谱、识别瓶颈、生成研究 Idea。

灵感来自 [Intern-Atlas (上海人工智能实验室)](https://arxiv.org/abs/2604.28158) 的方法演化图谱思路。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能

- 🔍 **论文自动搜索** — 输入研究方向，自动检索 15 篇代表性论文
- 🧠 **方法实体提取** — LLM 自动识别论文中的核心方法/技术
- 🔗 **演化关系识别** — 自动标注 extends/improves/replaces/adapts 关系
- 🚧 **瓶颈分析** — 识别方法演化中的关键瓶颈与未解决问题
- 💡 **Idea 生成** — 基于图谱空白点，生成创新研究提案
- 🗺️ **可视化图谱** — 交互式方法演化图谱（pyvis），支持颜色图例
- 📂 **历史记录管理** — 查看、对比、删除历史运行结果
- 📋 **论文导出** — 支持 BibTeX / CSV / JSON 格式导出
- 🔗 **论文链接自动补全** — 多源查找（S2 → CrossRef → OpenAlex）

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install flask networkx requests openai pyvis
```

### 2. 配置 API Key

本项目需要两个 API Key：

| API | 用途 | 获取地址 | 费用 |
|-----|------|---------|------|
| **DeepSeek** | 论文搜索 + 方法提取 + Idea 生成 | [platform.deepseek.com](https://platform.deepseek.com/) | 按量付费，~¥0.02/次 |
| **Semantic Scholar** | 论文链接自动补全（arXiv/DOI） | [semanticscholar.org](https://www.semanticscholar.org/product/api#api-key-form) | 免费 |

**配置方式（二选一）：**

**方式 A：直接编辑 `config.py`（推荐）**

```python
# config.py
DEEPSEEK_API_KEY = "sk-your-deepseek-key"
S2_API_KEY = "s2-your-s2-key"  # 可选，不填也能用（有速率限制）
```

**方式 B：环境变量**

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY = "sk-your-deepseek-key"
$env:S2_API_KEY = "s2-your-s2-key"

# Linux/macOS
export DEEPSEEK_API_KEY="sk-your-deepseek-key"
export S2_API_KEY="s2-your-s2-key"
```

### 3. 启动 Web 服务

```bash
python server.py
```

然后浏览器打开 **http://localhost:5000**

### 4. 或者命令行运行

```bash
# 快速模式（推荐，纯 LLM 驱动）
python fast.py "graph neural network for citation analysis"

# 完整模式（需要更多 API 调用）
python main.py "your research topic"
```

## 📁 项目结构

```
idea-lab/
├── server.py          # Web 服务 (Flask)
├── templates/
│   └── index.html     # 前端界面（模式选择 + 图谱可视化 + 论文导出）
├── fast.py            # 快速模式 pipeline（DeepSeek + S2 链接补全）
├── main.py            # 完整模式 pipeline（S2 引用图 + LLM 分析）
├── analyzer.py        # DeepSeek LLM 调用封装
├── graph_builder.py   # 引用图构建 (NetworkX)
├── scholar.py         # Semantic Scholar API 封装
├── config.py          # 配置文件（API Key 等，已 gitignore）
├── visualizer.py      # 图谱可视化（pyvis + SVG fallback + 颜色图例）
├── history.py         # 历史记录管理
└── output/            # 运行结果（JSON + Markdown 报告 + 图谱 HTML）
```

## ⚙️ 配置说明

在 `config.py` 中可调整：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | (必填) | DeepSeek API key |
| `S2_API_KEY` | (可选) | Semantic Scholar API key，不填有速率限制 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 使用的模型 |
| `MAX_IDEAS` | 5 | 生成 idea 数量 |
| `MAX_CITATION_DEPTH` | 2 | 完整模式引用图展开深度 |

## 🔧 工作原理

### 快速模式（推荐）

```
研究方向
  ↓
DeepSeek 搜索论文（标题 + 年份 + 方法，URL 留空）
  ↓
S2 → CrossRef → OpenAlex 多源查找真实链接（标题相似度验证）
  ↓
DeepSeek 构建方法演化图（方法 + 演化关系 + 瓶颈）
  ↓
DeepSeek 生成研究 Idea（动机 + 方法 + 预期贡献 + 评分）
  ↓
输出：JSON + Markdown 报告 + 交互式图谱
```

### 完整模式

```
研究方向
  ↓
S2 API 搜索论文 + 沿引用链展开（2 层深度）
  ↓
按引用数排序取 Top 论文
  ↓
LLM 逐篇提取方法实体
  ↓
LLM 基于引用关系识别演化边
  ↓
瓶颈分析 + Idea 生成
  ↓
输出：同上 + 引用图 JSON
```

### 论文链接查找策略

```
查询标题
  ↓
Semantic Scholar API（含标题相似度验证，阈值 0.4）
  ├─ 匹配 → arXiv > DOI > PubMed > ACL > DBLP > S2 URL
  └─ 不匹配 → CrossRef API
                  ├─ 匹配 → DOI
                  └─ 不匹配 → OpenAlex API
                                  ├─ 匹配 → DOI / OpenAlex URL
                                  └─ 不匹配 → Google Scholar 搜索（兜底）
```

核心思路来自 Intern-Atlas：
- **方法为原子单位**（不是论文模型）
- **四类演化关系**（extends/improves/replaces/adapts）
- **瓶颈-机制-权衡**三元组记录每条演化
- **基于图谱空白点**生成 idea（创新性+可行性评分）

## 📊 输出示例

每次运行生成：
- `result.json` — 结构化数据（论文、方法、演化图、idea）
- `report.md` — 可读 Markdown 报告
- `graph.html` — 交互式可视化图谱

### 图谱颜色说明

**节点 = 方法类别：**
| 颜色 | 类别 |
|------|------|
| 🟣 紫色 | architecture (架构) |
| 🟢 绿色 | training (训练) |
| 🟠 橙色 | optimization (优化) |
| 🟡 黄色 | data (数据) |
| 🔵 蓝色 | evaluation (评估) |

**连线 = 演化关系：**
| 颜色 | 关系 |
|------|------|
| 🟣 紫色 | extends (扩展) |
| 🟢 绿色 | improves (改进) |
| 🔴 红色 | replaces (替代) |
| 🟡 黄色 | adapts (适配) |
| 🔵 蓝色 | uses_component (组合) |

### Idea 格式

- 标题、动机、方法、预期贡献
- 相关方法、Gap 类型
- 新颖性评分 (1-10)、可行性评分 (1-10)

## 💰 费用说明

| 模式 | 调用次数 | 预估费用 |
|------|---------|---------|
| 快速模式 | ~6 次 DeepSeek | ~¥0.02 |
| 完整模式 | ~50 次 DeepSeek + S2 API | ~¥0.1-0.3 |

## 🙏 致谢

- [Intern-Atlas](https://arxiv.org/abs/2604.28158) — 方法演化图谱的理论基础
- [Semantic Scholar](https://www.semanticscholar.org/) — 学术论文 API
- [CrossRef](https://www.crossref.org/) — DOI 查找
- [OpenAlex](https://openalex.org/) — 开放学术数据
- [DeepSeek](https://platform.deepseek.com/) — LLM 服务

## 📄 License

MIT

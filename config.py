"""
IdeaLab 配置文件
"""
import os

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# Semantic Scholar API (免费，无需 key)
S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
S2_API_KEY = os.environ.get("S2_API_KEY", "")  # 可选，有 key 速率更高

# 图谱参数
MAX_PAPERS = 100          # 单次搜索最大论文数
MAX_CITATION_DEPTH = 2    # 引用图展开深度
MAX_IDEAS = 5             # 生成 idea 数量
YEAR_RANGE = (2020, 2025) # 默认年份范围

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

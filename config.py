"""
IdeaLab 配置文件
"""
import os
from datetime import datetime


def _load_dotenv() -> dict:
    """轻量读取项目根目录 .env，避免依赖 python-dotenv。"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    values = {}
    if not os.path.exists(env_path):
        return values

    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_DOTENV = _load_dotenv()

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") or _DOTENV.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# Semantic Scholar API (免费，无需 key)
S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
S2_API_KEY = os.environ.get("S2_API_KEY") or _DOTENV.get("S2_API_KEY", "")

# 图谱参数
MAX_PAPERS = 100          # 单次搜索最大论文数
MAX_CITATION_DEPTH = 2    # 引用图展开深度
MAX_IDEAS = 5             # 生成 idea 数量
CURRENT_YEAR = datetime.now().year
YEAR_RANGE = (CURRENT_YEAR - 5, CURRENT_YEAR)  # 默认年份范围

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fast import deepseek_search_papers

papers = deepseek_search_papers("graph neural network for citation analysis", n=5)
for p in papers:
    url = p.get("url", "N/A")
    print(f"[{p.get('year','?')}] {p.get('title','')[:60]}")
    print(f"  URL: {url}")
    print()

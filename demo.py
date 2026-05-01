"""
Demo — 不需要 API key，用模拟数据验证 pipeline
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime
from config import OUTPUT_DIR
from graph_builder import CitationGraph


def run_demo():
    """用模拟数据跑一遍完整流程"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(OUTPUT_DIR, f"demo_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    print("🔬 IdeaLab Demo (模拟数据)")
    print(f"   输出: {run_dir}\n")

    # ─── 构建模拟引用图 ─────────────────────────────────
    graph = CitationGraph()

    # 模拟论文数据
    papers = {
        "p001": {"title": "Attention Is All You Need", "year": 2017, "citations": 90000,
                 "abstract": "Proposed the Transformer architecture using self-attention mechanism.",
                 "authors": ["Vaswani", "Shazeer"]},
        "p002": {"title": "BERT: Pre-training of Deep Bidirectional Transformers", "year": 2018, "citations": 65000,
                 "abstract": "Bidirectional pre-training with masked language modeling.",
                 "authors": ["Devlin", "Chang"]},
        "p003": {"title": "GPT-2: Language Models are Unsupervised Multitask Learners", "year": 2019, "citations": 15000,
                 "abstract": "Scaled up language model shows zero-shot task transfer.",
                 "authors": ["Radford", "Wu"]},
        "p004": {"title": "Vision Transformer (ViT)", "year": 2020, "citations": 25000,
                 "abstract": "Apply pure transformer to image recognition with patch embeddings.",
                 "authors": ["Dosovitskiy", "Beyer"]},
        "p005": {"title": "LoRA: Low-Rank Adaptation of Large Language Models", "year": 2021, "citations": 12000,
                 "abstract": "Efficient fine-tuning by freezing weights and injecting trainable low-rank matrices.",
                 "authors": ["Hu", "Shen"]},
        "p006": {"title": "FlashAttention: Fast and Memory-Efficient Exact Attention", "year": 2022, "citations": 3000,
                 "abstract": "IO-aware attention algorithm that reduces memory from O(N^2) to O(N).",
                 "authors": ["Dao", "Fu"]},
        "p007": {"title": "Mamba: Linear-Time Sequence Modeling with Selective State Spaces", "year": 2023, "citations": 1500,
                 "abstract": "Selective SSM that replaces attention with input-dependent state selection.",
                 "authors": ["Gu", "Dao"]},
        "p008": {"title": "QLoRA: Efficient Finetuning of Quantized LLMs", "year": 2023, "citations": 2000,
                 "abstract": "4-bit quantized LoRA enabling finetuning on a single GPU.",
                 "authors": ["Dettmers", "Pagnoni"]},
        "p009": {"title": "Differential Transformer", "year": 2024, "citations": 300,
                 "abstract": "Differential attention mechanism that cancels noise by computing difference of two attention maps.",
                 "authors": ["Ye", "Li"]},
        "p010": {"title": "Native Sparse Attention (NSA)", "year": 2025, "citations": 50,
                 "abstract": "Hardware-aligned sparse attention with hierarchical token compression.",
                 "authors": ["Chen", "Liu"]},
    }

    for pid, meta in papers.items():
        graph.paper_meta[pid] = meta
        graph.paper_graph.add_node(pid)

    # 引用关系 (A -> B 表示 A 引用了 B)
    edges = [
        ("p002", "p001"),  # BERT -> Transformer
        ("p003", "p001"),  # GPT-2 -> Transformer
        ("p004", "p001"),  # ViT -> Transformer
        ("p004", "p002"),  # ViT -> BERT (借鉴预训练思路)
        ("p005", "p002"),  # LoRA -> BERT
        ("p005", "p003"),  # LoRA -> GPT-2
        ("p006", "p001"),  # FlashAttention -> Transformer
        ("p007", "p001"),  # Mamba -> Transformer (替代)
        ("p007", "p006"),  # Mamba -> FlashAttention
        ("p008", "p005"),  # QLoRA -> LoRA
        ("p009", "p001"),  # Diff Transformer -> Transformer
        ("p009", "p006"),  # Diff Transformer -> FlashAttention
        ("p010", "p001"),  # NSA -> Transformer
        ("p010", "p006"),  # NSA -> FlashAttention
        ("p010", "p009"),  # NSA -> Diff Transformer
    ]
    for src, tgt in edges:
        graph.paper_graph.add_edge(src, tgt)

    print(f"✓ 模拟图谱: {len(graph.paper_graph.nodes())} 节点, {len(graph.paper_graph.edges())} 边\n")

    # ─── 模拟方法提取 ────────────────────────────────────
    methods = {
        "Transformer": {"name": "Transformer", "category": "architecture", "novelty": "new",
                        "description": "Self-attention based sequence model replacing RNN/CNN"},
        "BERT": {"name": "BERT", "category": "pretraining", "novelty": "new",
                 "description": "Bidirectional masked language model pretraining"},
        "GPT": {"name": "GPT", "category": "pretraining", "novelty": "new",
                "description": "Autoregressive causal language model pretraining"},
        "ViT": {"name": "ViT", "category": "architecture", "novelty": "application",
                "description": "Transformer applied to image patches for vision tasks"},
        "LoRA": {"name": "LoRA", "category": "training_method", "novelty": "new",
                 "description": "Low-rank weight adaptation for efficient finetuning"},
        "FlashAttention": {"name": "FlashAttention", "category": "optimization", "novelty": "new",
                           "description": "IO-aware exact attention with tiling and recomputation"},
        "Selective SSM": {"name": "Selective SSM", "category": "architecture", "novelty": "new",
                          "description": "Input-dependent state space model for sequence modeling"},
        "QLoRA": {"name": "QLoRA", "category": "training_method", "novelty": "improvement",
                  "description": "4-bit quantized LoRA for single-GPU finetuning"},
        "Differential Attention": {"name": "Differential Attention", "category": "architecture", "novelty": "improvement",
                                    "description": "Noise-cancelling attention via difference of dual softmax"},
        "Native Sparse Attention": {"name": "Native Sparse Attention", "category": "optimization", "novelty": "improvement",
                                     "description": "Hardware-aligned hierarchical sparse attention"},
    }

    for name, m in methods.items():
        graph.method_graph.add_node(name, **m)

    # ─── 模拟演化关系 ────────────────────────────────────
    evolution_edges = [
        ("Transformer", "BERT", "extends",
         "Transformer needs task-specific finetuning",
         "Bidirectional masked pretraining then finetune",
         "Requires labeled data for each task"),
        ("Transformer", "GPT", "extends",
         "Transformer not designed for generation",
         "Autoregressive causal masking",
         "Cannot capture bidirectional context"),
        ("Transformer", "ViT", "adapts",
         "CNN dominates vision, Transformer untested",
         "Split images into patches, treat as tokens",
         "Needs large-scale data to work well"),
        ("Transformer", "FlashAttention", "improves",
         "Standard attention is O(N^2) memory",
         "Tiled recomputation to avoid materializing attention matrix",
         "Requires custom CUDA kernels"),
        ("LoRA", "QLoRA", "improves",
         "LoRA still uses full-precision base model",
         "4-bit NormalFloat quantization + LoRA",
         "Slight quality loss from quantization"),
        ("Transformer", "Selective SSM", "replaces",
         "Attention is quadratic in sequence length",
         "Input-dependent state selection gate",
         "No explicit attention heads for in-context retrieval"),
        ("FlashAttention", "Differential Attention", "improves",
         "FlashAttention still computes full dense attention",
         "Difference of two softmax attention maps cancels noise",
         "Additional computation for dual attention"),
        ("FlashAttention", "Native Sparse Attention", "improves",
         "Dense attention wastes compute on irrelevant tokens",
         "Hierarchical token compression + hardware-aligned sparsity",
         "Sparse pattern may miss long-tail dependencies"),
        ("Differential Attention", "Native Sparse Attention", "improves",
         "Differential attention still O(N^2)",
         "Combine differential mechanism with sparse pattern",
         "Complexity of combining two mechanisms"),
    ]

    for src, tgt, rel, bottleneck, mechanism, tradeoff in evolution_edges:
        graph.method_graph.add_edge(tgt, src,
            relation=rel, bottleneck=bottleneck,
            mechanism=mechanism, tradeoff=tradeoff, confidence=0.9)

    print(f"✓ 方法: {len(methods)} 个")
    print(f"✓ 演化边: {len(evolution_edges)} 条\n")

    # ─── 生成报告 ────────────────────────────────────────
    # 模拟 idea
    ideas = [
        {
            "title": "Differential Sparse Attention: Noise-Cancelling Meets Sparsity",
            "motivation": "Differential Attention cancels noise but is O(N^2); Native Sparse Attention is efficient but may miss dependencies. Combining both could yield O(N) attention with noise cancellation.",
            "approach": "Apply differential attention mechanism only to the sparse attention pattern selected by NSA, reducing both noise and compute.",
            "expected_contribution": "Linear-time attention with better quality than either approach alone",
            "related_methods": ["Differential Attention", "Native Sparse Attention", "FlashAttention"],
            "gap_type": "cross_pollination",
            "novelty_score": 7,
            "feasibility_score": 6,
        },
        {
            "title": "LoRA-SSM: Low-Rank Adaptation for State Space Models",
            "motivation": "LoRA works well for Transformer finetuning but has not been systematically applied to SSM architectures like Mamba.",
            "approach": "Identify the low-rank structure in SSM state matrices and design parameter-efficient adaptation for selective SSMs.",
            "expected_contribution": "Enable efficient finetuning of large SSM models with minimal parameters",
            "related_methods": ["LoRA", "Selective SSM", "QLoRA"],
            "gap_type": "trend_extrapolation",
            "novelty_score": 6,
            "feasibility_score": 8,
        },
        {
            "title": "Patch-Free Vision Transformer with Hierarchical Token Compression",
            "motivation": "ViT's fixed patch size limits its ability to capture multi-scale features. NSA's hierarchical compression could address this.",
            "approach": "Replace fixed patch embedding with hierarchical token compression that adapts to image content, using sparse attention for efficiency.",
            "expected_contribution": "Better multi-scale representation without computational overhead",
            "related_methods": ["ViT", "Native Sparse Attention", "Selective SSM"],
            "gap_type": "cross_pollination",
            "novelty_score": 7,
            "feasibility_score": 5,
        },
        {
            "title": "Bidirectional Selective SSM for Language Understanding",
            "motivation": "Selective SSM (Mamba) is unidirectional; BERT showed bidirectional context is crucial for understanding tasks.",
            "approach": "Design a bidirectional scanning strategy for selective SSMs with learned direction mixing.",
            "expected_contribution": "SSM-based language understanding matching BERT-level quality with linear complexity",
            "related_methods": ["Selective SSM", "BERT", "GPT"],
            "gap_type": "bottleneck_resolution",
            "novelty_score": 8,
            "feasibility_score": 5,
        },
    ]

    # 写报告
    report_path = os.path.join(run_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# IdeaLab Demo 研究报告\n\n")
        f.write(f"**查询:** Transformer evolution & efficiency\n")
        f.write(f"**时间:** {timestamp}\n")
        f.write(f"**论文数:** {len(papers)} (模拟)\n")
        f.write(f"**方法数:** {len(methods)}\n")
        f.write(f"**演化边:** {len(evolution_edges)}\n\n")

        f.write("## 方法演化图\n\n")
        f.write("```")
        f.write("\nAttention Is All You Need (2017)")
        f.write("\n  ├──→ BERT (2018, bidirectional pretraining)")
        f.write("\n  ├──→ GPT (2019, autoregressive)")
        f.write("\n  ├──→ ViT (2020, vision adaptation)")
        f.write("\n  ├──→ FlashAttention (2022, O(N) memory)")
        f.write("\n  │      ├──→ Differential Attention (2024, noise cancellation)")
        f.write("\n  │      └──→ Native Sparse Attention (2025, hardware-aligned sparsity)")
        f.write("\n  └──→ Selective SSM / Mamba (2023, replaces attention)")
        f.write("\n")
        f.write("\nLoRA (2021) → QLoRA (2023, quantized)")
        f.write("\n```\n\n")

        f.write("## 演化关系详情\n\n")
        for src, tgt, rel, bottleneck, mechanism, tradeoff in evolution_edges:
            f.write(f"### {tgt} →[{rel}]→ {src}\n")
            f.write(f"- **瓶颈:** {bottleneck}\n")
            f.write(f"- **机制:** {mechanism}\n")
            f.write(f"- **权衡:** {tradeoff}\n\n")

        f.write("## 研究 Idea\n\n")
        for i, idea in enumerate(ideas, 1):
            f.write(f"### {i}. {idea['title']}\n\n")
            f.write(f"**动机:** {idea['motivation']}\n\n")
            f.write(f"**方法:** {idea['approach']}\n\n")
            f.write(f"**预期贡献:** {idea['expected_contribution']}\n\n")
            f.write(f"**相关方法:** {', '.join(idea['related_methods'])}\n\n")
            f.write(f"**Gap 类型:** {idea['gap_type']} | **新颖性:** {idea['novelty_score']}/10 | **可行性:** {idea['feasibility_score']}/10\n\n")
            f.write("---\n\n")

    # 保存 JSON
    result_path = os.path.join(run_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump({
            "methods": methods,
            "evolution_edges": [
                {"from": s, "to": t, "relation": r, "bottleneck": b, "mechanism": m, "tradeoff": tr}
                for s, t, r, b, m, tr in evolution_edges
            ],
            "ideas": ideas,
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ Demo 完成!")
    print(f"   报告: {report_path}")
    print(f"   数据: {result_path}")
    print(f"\n{'='*60}")
    print("  研究 Idea 预览:")
    print(f"{'='*60}")
    for i, idea in enumerate(ideas, 1):
        print(f"\n  {i}. {idea['title']}")
        print(f"     类型: {idea['gap_type']} | 新颖性: {idea['novelty_score']}/10 | 可行性: {idea['feasibility_score']}/10")


if __name__ == "__main__":
    run_demo()

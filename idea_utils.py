"""
Idea 后处理：轻量 novelty filter 与重排序
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from method_utils import canonicalize_method_name


def _normalize_related_methods(idea: dict) -> List[str]:
    related = []
    for name in idea.get("related_methods", []) or []:
        canonical = canonicalize_method_name(name)
        if canonical and canonical not in related:
            related.append(canonical)
    return related


def _edge_index(edges: List[Dict]) -> Set[Tuple[str, str]]:
    return {
        (canonicalize_method_name(edge.get("source", "")), canonicalize_method_name(edge.get("target", "")))
        for edge in (edges or [])
        if edge.get("source") and edge.get("target")
    }


def annotate_and_rerank_ideas(ideas: List[Dict], methods: List[Dict], edges: List[Dict], max_ideas: Optional[int] = None) -> List[Dict]:
    """对 ideas 做轻量 novelty 惩罚和解释性标注。"""
    edge_pairs = _edge_index(edges)
    known_methods = {
        canonicalize_method_name(method.get("name", ""))
        for method in (methods or [])
        if method.get("name")
    }

    annotated = []
    for raw_idea in ideas or []:
        idea = dict(raw_idea)
        related_methods = _normalize_related_methods(idea)
        idea["related_methods"] = related_methods

        existing_pair_hits = 0
        for src in related_methods:
            for tgt in related_methods:
                if src != tgt and (src, tgt) in edge_pairs:
                    existing_pair_hits += 1

        unknown_methods = [m for m in related_methods if m and m not in known_methods]
        base_novelty = int(idea.get("novelty_score", 0) or 0)
        feasibility = int(idea.get("feasibility_score", 0) or 0)

        novelty_penalty = 0
        notes = []
        if existing_pair_hits >= 2:
            novelty_penalty += 2
            notes.append("related_methods highly overlap with existing evolution edges")
        elif existing_pair_hits == 1:
            novelty_penalty += 1
            notes.append("partly overlaps with an existing evolution edge")

        if len(related_methods) <= 1:
            novelty_penalty += 1
            notes.append("too few related methods to establish a non-trivial bridge")

        if unknown_methods:
            notes.append(f"mentions out-of-graph methods: {', '.join(unknown_methods[:3])}")

        adjusted_novelty = max(1, min(10, base_novelty - novelty_penalty))
        idea["novelty_score_raw"] = base_novelty
        idea["novelty_penalty"] = novelty_penalty
        idea["novelty_score"] = adjusted_novelty
        idea["novelty_rationale"] = "; ".join(notes) if notes else "keeps enough distance from current graph edges"
        idea["selection_score"] = adjusted_novelty * 0.7 + feasibility * 0.3
        annotated.append(idea)

    annotated.sort(key=lambda item: (item.get("selection_score", 0), item.get("novelty_score", 0), item.get("feasibility_score", 0)), reverse=True)
    if max_ideas is not None:
        annotated = annotated[:max_ideas]
    return annotated

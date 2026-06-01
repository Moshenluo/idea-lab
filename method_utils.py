"""
方法归一化与图谱结构清洗工具
"""
from __future__ import annotations

import re


ALIAS_OVERRIDES = {
    "low-rank adaptation": "LoRA",
    "low rank adaptation": "LoRA",
    "lora": "LoRA",
    "qlora": "QLoRA",
    "flash attention": "FlashAttention",
    "flashattention": "FlashAttention",
    "flashattention-2": "FlashAttention-2",
    "selective state space model": "Selective SSM",
    "selective state space models": "Selective SSM",
    "selective ssm": "Selective SSM",
    "mamba": "Mamba",
    "vision transformer": "ViT",
    "vit": "ViT",
    "graph neural network": "GNN",
    "graph neural networks": "GNN",
    "gnn": "GNN",
    "large language model": "LLM",
    "large language models": "LLM",
    "llm": "LLM",
    "retrieval augmented generation": "RAG",
    "retrieval-augmented generation": "RAG",
    "rag": "RAG",
}


def _clean_name(name: str) -> str:
    text = (name or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -_:;,.")


def canonicalize_method_name(name: str) -> str:
    cleaned = _clean_name(name)
    lowered = cleaned.lower()
    if lowered in ALIAS_OVERRIDES:
        return ALIAS_OVERRIDES[lowered]
    if cleaned.isupper() and len(cleaned) <= 8:
        return cleaned
    words = [w for w in re.split(r"\s+", cleaned) if w]
    if len(words) == 1:
        return cleaned
    return " ".join(word if word.isupper() else word.capitalize() for word in words)


def normalize_method_record(method: dict) -> dict:
    normalized = dict(method or {})
    original_name = normalized.get("name", "")
    canonical = canonicalize_method_name(original_name)
    aliases = normalized.get("aliases", []) or []
    alias_values = []
    for alias in [original_name, canonical, *aliases]:
        alias = _clean_name(alias)
        if alias and alias not in alias_values:
            alias_values.append(alias)

    normalized["name"] = canonical
    normalized["canonical_name"] = canonical
    normalized["aliases"] = alias_values
    return normalized


def merge_method_records(existing: dict, incoming: dict) -> dict:
    merged = dict(existing or {})
    new_item = normalize_method_record(incoming)

    for key in ["name", "canonical_name", "description", "category", "novelty", "year", "first_paper"]:
        if not merged.get(key) and new_item.get(key):
            merged[key] = new_item[key]

    merged_aliases = []
    for alias in [*(merged.get("aliases", []) or []), *(new_item.get("aliases", []) or [])]:
        alias = _clean_name(alias)
        if alias and alias not in merged_aliases:
            merged_aliases.append(alias)
    merged["aliases"] = merged_aliases
    merged["name"] = merged.get("canonical_name") or new_item["canonical_name"]
    merged["canonical_name"] = merged.get("name")
    return merged


def normalize_methods_list(methods: list[dict]) -> list[dict]:
    merged = {}
    for method in methods or []:
        record = normalize_method_record(method)
        key = record["canonical_name"]
        merged[key] = merge_method_records(merged.get(key, {}), record)
    return list(merged.values())


def normalize_edge_record(edge: dict) -> dict:
    normalized = dict(edge or {})
    normalized["source"] = canonicalize_method_name(normalized.get("source", ""))
    normalized["target"] = canonicalize_method_name(normalized.get("target", ""))
    normalized["relation"] = (normalized.get("relation") or "").strip()
    normalized["bottleneck"] = (normalized.get("bottleneck") or "").strip()
    normalized["mechanism"] = (normalized.get("mechanism") or "").strip()
    normalized["trade_off"] = (normalized.get("trade_off") or "").strip()
    normalized["evidence"] = (normalized.get("evidence") or "").strip()
    for key in ["source_paper_ids", "target_paper_ids", "source_paper_titles", "target_paper_titles"]:
        value = normalized.get(key, []) or []
        if not isinstance(value, list):
            value = [value]
        cleaned = []
        for item in value:
            item = str(item).strip()
            if item and item not in cleaned:
                cleaned.append(item)
        normalized[key] = cleaned
    return normalized


def dedupe_edges(edges: list[dict]) -> list[dict]:
    deduped = {}
    for edge in edges or []:
        normalized = normalize_edge_record(edge)
        if not normalized["source"] or not normalized["target"]:
            continue
        key = (normalized["source"], normalized["target"], normalized["relation"])
        existing = deduped.get(key)
        if not existing:
            deduped[key] = normalized
            continue

        winner, loser = (
            (normalized, existing)
            if normalized.get("confidence", 0) > existing.get("confidence", 0)
            else (existing, normalized)
        )
        merged = dict(winner)
        for field in ["source_paper_ids", "target_paper_ids", "source_paper_titles", "target_paper_titles"]:
            values = []
            for item in [*(winner.get(field, []) or []), *(loser.get(field, []) or [])]:
                if item and item not in values:
                    values.append(item)
            merged[field] = values
        if not merged.get("evidence") and loser.get("evidence"):
            merged["evidence"] = loser["evidence"]
        deduped[key] = merged
    return list(deduped.values())

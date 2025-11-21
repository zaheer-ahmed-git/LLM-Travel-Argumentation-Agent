"""Compress agent messages to reduce communication overhead."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CompressionResult:
    text: str
    original_size: int
    compressed_size: int
    ratio: float
    compressed: bool


class ContextCompressor:
    """Lightweight extractive compressor for inter-agent payloads.

    Targets ~40% less communication overhead by keeping salient sentences
    and dropping filler / repeated whitespace.
    """

    FILLER = re.compile(
        r"\b(basically|actually|really|very|just|kind of|sort of|in order to)\b",
        re.IGNORECASE,
    )

    def __init__(self, max_chars: int = 800, target_ratio: float = 0.6) -> None:
        self.max_chars = max_chars
        self.target_ratio = target_ratio

    def compress(self, text: str) -> CompressionResult:
        original = text or ""
        original_size = len(original)
        if original_size == 0:
            return CompressionResult("", 0, 0, 1.0, False)

        cleaned = self.FILLER.sub("", original)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        # Prefer sentences with action / decision keywords
        scored = sorted(
            sentences,
            key=lambda s: self._score(s),
            reverse=True,
        )
        kept: list[str] = []
        size = 0
        budget = min(self.max_chars, max(1, int(original_size * self.target_ratio)))
        for sentence in scored:
            if not sentence:
                continue
            candidate = len(sentence) + (1 if kept else 0)
            if size + candidate > budget and kept:
                break
            kept.append(sentence)
            size += candidate

        # Preserve relative order of selected sentences
        order = {s: i for i, s in enumerate(sentences)}
        kept.sort(key=lambda s: order.get(s, 0))
        compressed_text = " ".join(kept).strip() or cleaned[:budget]
        compressed_size = len(compressed_text)
        ratio = compressed_size / original_size if original_size else 1.0
        return CompressionResult(
            text=compressed_text,
            original_size=original_size,
            compressed_size=compressed_size,
            ratio=ratio,
            compressed=compressed_size < original_size,
        )

    @staticmethod
    def _score(sentence: str) -> float:
        keywords = (
            "must",
            "should",
            "deliver",
            "result",
            "risk",
            "deadline",
            "approve",
            "reject",
            "metric",
            "next",
            "action",
            "summary",
        )
        lower = sentence.lower()
        hits = sum(1 for k in keywords if k in lower)
        return hits * 2.0 + min(len(sentence), 120) / 120.0

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TokenDistiller: 网页与长文档 Token 噪声极速蒸馏装具
===================================================
源自 AI 集群 omniscout-radar / web_distiller 核心模块。
在 LLM 消费长网页、API 手册或爬虫返回内容前，剥离 85%~90% 的无用 HTML/DOM 噪声。
纯标准库实现，零外部依赖。
"""

import re
from typing import Dict, Any


class DistillResult:
    def __init__(self, cleaned_text: str, raw_bytes: int, cleaned_bytes: int, compression_ratio_pct: float):
        self.cleaned_text = cleaned_text
        self.raw_bytes = raw_bytes
        self.cleaned_bytes = cleaned_bytes
        self.compression_ratio_pct = compression_ratio_pct

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_bytes": self.raw_bytes,
            "cleaned_bytes": self.cleaned_bytes,
            "compression_ratio_pct": self.compression_ratio_pct,
            "content_preview": self.cleaned_text[:200] + "..." if len(self.cleaned_text) > 200 else self.cleaned_text
        }


class TokenDistiller:
    @staticmethod
    def distill_html(html_content: str) -> DistillResult:
        """Strip HTML tags, scripts, styles, SVGs and collapse whitespace."""
        raw_len = len(html_content.encode("utf-8"))

        # 1. Remove script, style, nav, footer, header, svg, noscript, iframe
        content = re.sub(
            r"<(script|style|nav|footer|header|svg|noscript|iframe|select|option)[^>]*>.*?</\1>",
            "",
            html_content,
            flags=re.DOTALL | re.IGNORECASE
        )
        # 2. Remove HTML comments
        content = re.sub(r"<!--[\s\S]*?-->", "", content)
        # 3. Convert headers and paragraphs into clean newlines
        content = re.sub(r"</?(?:h[1-6]|p|div|li|tr|br)[^>]*>", "\n", content, flags=re.IGNORECASE)
        # 4. Remove all other remaining HTML tags
        content = re.sub(r"<[^>]+>", " ", content)
        # 5. Decode common HTML entities
        content = content.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"")
        # 6. Normalize spaces and excessive newlines
        content = re.sub(r"[ \t]+", " ", content)
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)
        cleaned = content.strip()

        clean_len = len(cleaned.encode("utf-8"))
        ratio = round(((raw_len - clean_len) / max(raw_len, 1)) * 100, 2)

        return DistillResult(
            cleaned_text=cleaned,
            raw_bytes=raw_len,
            cleaned_bytes=clean_len,
            compression_ratio_pct=ratio
        )

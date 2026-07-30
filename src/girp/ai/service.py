from __future__ import annotations

from typing import Any

from .formula_explainer import DebugResult, debug_formula, explain_formula
from .provider import AIProvider, get_provider

SYSTEM_PROMPTS = {
    "en": (
        "You are an assistant embedded in GUMPOL_ระบบคัดกรองหุ้น, a stock screening/ranking/"
        "valuation/backtesting tool. Be concise, concrete, and grounded only in the numbers "
        "given to you. Never give direct buy/sell investment advice — describe what the data "
        "shows and let the user decide. This formula language only supports a flat AND/OR "
        "chain of comparisons (field OP value [AND|OR field OP value ...]) — no parentheses."
    ),
    "th": (
        "คุณเป็นผู้ช่วยในระบบ GUMPOL_ระบบคัดกรองหุ้น เครื่องมือคัดกรอง/จัดอันดับ/ประเมินมูลค่า/"
        "ทดสอบย้อนหลังหุ้น ตอบให้กระชับ ชัดเจน อิงจากตัวเลขที่ได้รับเท่านั้น ห้ามให้คำแนะนำซื้อ/ขาย"
        "โดยตรง ให้บรรยายสิ่งที่ข้อมูลบ่งชี้แล้วให้ผู้ใช้ตัดสินใจเอง สูตรของระบบนี้รองรับเฉพาะเงื่อนไข "
        "แบบ AND/OR เรียงต่อกัน (field OP value [AND|OR field OP value ...]) ไม่รองรับวงเล็บ"
    ),
}


class AIService:
    """Wraps an AIProvider plus the deterministic formula explainer.

    explain_formula/debug_formula work with no configured provider at all (pure
    dataclass/regex logic, no LLM call). summarize/compare/suggest_strategy/optimize_strategy
    require a configured provider and will raise AIProviderNotConfigured (from
    girp.ai.provider) if none is set — callers (the API layer) should catch that and
    return a 503 with a clear message.
    """

    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider if provider is not None else get_provider()

    # -- deterministic, no LLM required -----------------------------------------------

    def explain_formula(self, source: str, lang: str = "en") -> str:
        return explain_formula(source, lang=lang)

    def debug_formula(self, source: str, lang: str = "en") -> DebugResult:
        return debug_formula(source, lang=lang)

    # -- LLM-backed ---------------------------------------------------------------------

    def summarize(self, symbol: str, metrics: dict[str, Any], lang: str = "en") -> str:
        metric_lines = "\n".join(f"- {key}: {value}" for key, value in metrics.items() if value is not None)
        if lang == "en":
            prompt = (
                f"Summarize the current situation for stock {symbol} based on these metrics:\n"
                f"{metric_lines}\n\n"
                "Write 3-5 short sentences covering valuation, quality, and momentum/trend, "
                "in plain language a non-expert investor can follow."
            )
        else:
            prompt = (
                f"สรุปสถานการณ์ปัจจุบันของหุ้น {symbol} จากตัวชี้วัดต่อไปนี้:\n"
                f"{metric_lines}\n\n"
                "เขียนสรุป 3-5 ประโยคสั้นๆ ครอบคลุมด้านมูลค่า คุณภาพ และโมเมนตัม/แนวโน้ม "
                "ด้วยภาษาที่นักลงทุนทั่วไปเข้าใจง่าย"
            )
        return self._provider.complete(prompt, system=SYSTEM_PROMPTS[lang])

    def compare(self, symbols: list[str], metrics_by_symbol: dict[str, dict[str, Any]], lang: str = "en") -> str:
        blocks = []
        for symbol in symbols:
            metrics = metrics_by_symbol.get(symbol, {})
            lines = "\n".join(f"  - {key}: {value}" for key, value in metrics.items() if value is not None)
            blocks.append(f"{symbol}:\n{lines}")
        joined = "\n\n".join(blocks)
        if lang == "en":
            prompt = (
                f"Compare these stocks based on their metrics:\n\n{joined}\n\n"
                "Highlight the key differences in valuation, quality, and momentum. "
                "Present as a short structured comparison, not a recommendation."
            )
        else:
            prompt = (
                f"เปรียบเทียบหุ้นเหล่านี้จากตัวชี้วัด:\n\n{joined}\n\n"
                "เน้นความแตกต่างสำคัญด้านมูลค่า คุณภาพ และโมเมนตัม "
                "นำเสนอเป็นการเปรียบเทียบแบบมีโครงสร้างสั้นๆ ไม่ใช่คำแนะนำการลงทุน"
            )
        return self._provider.complete(prompt, system=SYSTEM_PROMPTS[lang])

    def suggest_strategy(self, goal: str, lang: str = "en") -> str:
        known_fields_hint = (
            "Only use field names that exist in this system (e.g. close, sma_20, ema_20, rsi_14, "
            "macd, macd_histogram, adx_14, bollinger_percent_b_20, cci_20, mfi_14, supertrend_direction, "
            "pe, pbv, roe, roa, revenue_growth, piotroski_f_score, altman_z_score, beneish_m_score, "
            "score_quality, score_growth, score_value, score_momentum, score_risk, score_overall, "
            "sector, asset_type, country, industry, exchange)."
        )
        if lang == "en":
            prompt = (
                f"A user wants a stock screening strategy for this goal: \"{goal}\"\n\n"
                f"Propose 1-2 candidate formulas in this system's flat AND/OR syntax "
                f"(field OP value [AND|OR field OP value ...], no parentheses, text values in double quotes). "
                f"{known_fields_hint}\n"
                "Briefly explain the reasoning behind each formula."
            )
        else:
            prompt = (
                f"ผู้ใช้ต้องการกลยุทธ์คัดกรองหุ้นสำหรับเป้าหมายนี้: \"{goal}\"\n\n"
                f"เสนอสูตร 1-2 แบบในรูปแบบ AND/OR เรียงต่อกันของระบบนี้ "
                f"(field OP value [AND|OR field OP value ...] ไม่มีวงเล็บ ค่าข้อความใส่เครื่องหมายคำพูดคู่) "
                f"{known_fields_hint}\n"
                "อธิบายเหตุผลของแต่ละสูตรสั้นๆ"
            )
        return self._provider.complete(prompt, system=SYSTEM_PROMPTS[lang])

    def optimize_strategy(
        self, formula: str, backtest_metrics: dict[str, Any], lang: str = "en"
    ) -> str:
        metric_lines = "\n".join(f"- {key}: {value}" for key, value in backtest_metrics.items() if value is not None)
        if lang == "en":
            prompt = (
                f"This formula was backtested: {formula}\n\nResults:\n{metric_lines}\n\n"
                "Suggest 1-2 concrete adjustments (threshold changes, added/removed conditions) "
                "that could plausibly improve the risk-adjusted return, staying within this "
                "system's flat AND/OR syntax (no parentheses). Explain the tradeoff of each suggestion."
            )
        else:
            prompt = (
                f"สูตรนี้ถูกทดสอบย้อนหลัง: {formula}\n\nผลลัพธ์:\n{metric_lines}\n\n"
                "แนะนำการปรับปรุง 1-2 อย่างที่เป็นรูปธรรม (เปลี่ยนค่า threshold, เพิ่ม/ลดเงื่อนไข) "
                "ที่อาจช่วยเพิ่มผลตอบแทนเทียบความเสี่ยง โดยยังอยู่ในรูปแบบ AND/OR เรียงต่อกันของระบบ "
                "(ไม่มีวงเล็บ) อธิบาย tradeoff ของแต่ละข้อเสนอ"
            )
        return self._provider.complete(prompt, system=SYSTEM_PROMPTS[lang])

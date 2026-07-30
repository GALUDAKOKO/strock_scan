from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from girp.formula.parser import Comparison, Formula, ParseError, parse_formula

# Each entry: field -> (English label, Thai label)
FIELD_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    # price / volume
    "close": ("closing price", "ราคาปิด"),
    "volume": ("trading volume", "ปริมาณการซื้อขาย"),
    # moving averages / momentum
    "sma_20": ("20-period simple moving average", "เส้นค่าเฉลี่ยเคลื่อนที่แบบง่าย 20 วัน (SMA 20)"),
    "ema_20": ("20-period exponential moving average", "เส้นค่าเฉลี่ยเคลื่อนที่แบบเอ็กซ์โพเนนเชียล 20 วัน (EMA 20)"),
    "rsi_14": ("14-period Relative Strength Index", "ดัชนีความแข็งแกร่งสัมพัทธ์ 14 วัน (RSI 14)"),
    "close_vs_sma_20": ("closing price relative to SMA 20 (%)", "ราคาปิดเทียบกับ SMA 20 (%)"),
    "close_vs_ema_20": ("closing price relative to EMA 20 (%)", "ราคาปิดเทียบกับ EMA 20 (%)"),
    "momentum_score": ("composite momentum score", "คะแนนโมเมนตัมรวม"),
    # volatility
    "atr_14": ("14-period Average True Range", "ค่าพิสัยเฉลี่ยจริง 14 วัน (ATR 14)"),
    "bollinger_middle_20": ("Bollinger Band middle line (20-period SMA)", "เส้นกลางแถบโบลินเจอร์ (SMA 20 วัน)"),
    "bollinger_upper_20": ("Bollinger Band upper line", "แถบโบลินเจอร์ด้านบน"),
    "bollinger_lower_20": ("Bollinger Band lower line", "แถบโบลินเจอร์ด้านล่าง"),
    "bollinger_percent_b_20": ("position within Bollinger Bands (%B)", "ตำแหน่งราคาภายในแถบโบลินเจอร์ (%B)"),
    "adx_14": ("14-period Average Directional Index (trend strength)", "ดัชนีวัดความแข็งแกร่งของแนวโน้ม 14 วัน (ADX 14)"),
    "plus_di_14": ("+DI (positive directional indicator)", "+DI (ตัวชี้วัดทิศทางบวก)"),
    "minus_di_14": ("-DI (negative directional indicator)", "-DI (ตัวชี้วัดทิศทางลบ)"),
    # oscillators
    "macd": ("MACD line", "เส้น MACD"),
    "macd_signal": ("MACD signal line", "เส้นสัญญาณ MACD"),
    "macd_histogram": ("MACD histogram (MACD minus signal)", "ฮิสโตแกรม MACD (MACD ลบเส้นสัญญาณ)"),
    "cci_20": ("20-period Commodity Channel Index", "ดัชนีช่องทางสินค้าโภคภัณฑ์ 20 วัน (CCI 20)"),
    # volume indicators
    "obv": ("On-Balance Volume", "ปริมาณการซื้อขายสะสม (OBV)"),
    "vwap": ("Volume Weighted Average Price", "ราคาเฉลี่ยถ่วงน้ำหนักด้วยปริมาณ (VWAP)"),
    "mfi_14": ("14-period Money Flow Index", "ดัชนีกระแสเงิน 14 วัน (MFI 14)"),
    # trend
    "ichimoku_tenkan_sen": ("Ichimoku conversion line (Tenkan-sen)", "เส้นแปลง Ichimoku (Tenkan-sen)"),
    "ichimoku_kijun_sen": ("Ichimoku base line (Kijun-sen)", "เส้นฐาน Ichimoku (Kijun-sen)"),
    "ichimoku_senkou_span_a": ("Ichimoku leading span A", "เส้นนำ A ของ Ichimoku (Senkou Span A)"),
    "ichimoku_senkou_span_b": ("Ichimoku leading span B", "เส้นนำ B ของ Ichimoku (Senkou Span B)"),
    "ichimoku_chikou_span": ("Ichimoku lagging span", "เส้นตาม Ichimoku (Chikou Span)"),
    "supertrend": ("Supertrend line value", "ค่าเส้น Supertrend"),
    "supertrend_direction": ("Supertrend direction (1 = up, -1 = down)", "ทิศทาง Supertrend (1 = ขึ้น, -1 = ลง)"),
    "pivot": ("classic pivot point", "จุดหมุน (Pivot Point)"),
    "pivot_r1": ("first resistance level above pivot", "แนวต้านที่ 1 เหนือจุดหมุน"),
    "pivot_r2": ("second resistance level above pivot", "แนวต้านที่ 2 เหนือจุดหมุน"),
    "pivot_s1": ("first support level below pivot", "แนวรับที่ 1 ใต้จุดหมุน"),
    "pivot_s2": ("second support level below pivot", "แนวรับที่ 2 ใต้จุดหมุน"),
    "support_20": ("20-period rolling support level", "แนวรับหมุนเวียน 20 วัน"),
    "resistance_20": ("20-period rolling resistance level", "แนวต้านหมุนเวียน 20 วัน"),
    # patterns (0/1 flags)
    "pattern_doji": ("Doji candlestick pattern flag", "สัญลักษณ์แท่งเทียนโดจิ"),
    "pattern_hammer": ("Hammer candlestick pattern flag", "สัญลักษณ์แท่งเทียนแฮมเมอร์"),
    "pattern_shooting_star": ("Shooting Star candlestick pattern flag", "สัญลักษณ์แท่งเทียนดาวตก"),
    "pattern_bullish_engulfing": ("Bullish Engulfing candlestick pattern flag", "สัญลักษณ์แท่งเทียนกลืนกินขาขึ้น"),
    "pattern_bearish_engulfing": ("Bearish Engulfing candlestick pattern flag", "สัญลักษณ์แท่งเทียนกลืนกินขาลง"),
    # fundamentals
    "price": ("share price", "ราคาหุ้น"),
    "pe": ("Price-to-Earnings ratio", "อัตราส่วนราคาต่อกำไร (P/E)"),
    "pbv": ("Price-to-Book-Value ratio", "อัตราส่วนราคาต่อมูลค่าทางบัญชี (P/BV)"),
    "roe": ("Return on Equity (%)", "อัตราผลตอบแทนต่อส่วนของผู้ถือหุ้น (ROE)"),
    "roa": ("Return on Assets (%)", "อัตราผลตอบแทนต่อสินทรัพย์ (ROA)"),
    "roic": ("Return on Invested Capital (%)", "อัตราผลตอบแทนต่อเงินลงทุน (ROIC)"),
    "net_margin": ("net profit margin (%)", "อัตรากำไรสุทธิ (%)"),
    "revenue_growth": ("year-over-year revenue growth (%)", "อัตราการเติบโตของรายได้ (%)"),
    "asset_growth": ("year-over-year total asset growth (%)", "อัตราการเติบโตของสินทรัพย์รวม (%)"),
    "current_ratio": ("current ratio (liquidity)", "อัตราส่วนสภาพคล่อง (Current Ratio)"),
    "debt_to_equity": ("debt-to-equity ratio", "อัตราส่วนหนี้สินต่อทุน (D/E)"),
    "free_cash_flow": ("free cash flow", "กระแสเงินสดอิสระ"),
    "owner_earnings": ("owner earnings (Buffett-style)", "กำไรของเจ้าของกิจการ (Owner Earnings)"),
    "market_cap": ("market capitalization", "มูลค่าตลาดรวม (Market Cap)"),
    "dividend_yield": ("dividend yield (%)", "อัตราผลตอบแทนเงินปันผล (%)"),
    "beta": ("beta (volatility relative to market)", "ค่าเบต้า (ความผันผวนเทียบตลาด)"),
    "piotroski_f_score": ("Piotroski F-Score (0-9, financial strength)", "คะแนน Piotroski F-Score (0-9, ความแข็งแกร่งทางการเงิน)"),
    "altman_z_score": ("Altman Z-Score (bankruptcy risk)", "คะแนน Altman Z-Score (ความเสี่ยงล้มละลาย)"),
    "beneish_m_score": ("Beneish M-Score (earnings manipulation risk)", "คะแนน Beneish M-Score (ความเสี่ยงตกแต่งกำไร)"),
    # valuation
    "graham_number": ("Graham Number fair value estimate", "มูลค่ายุติธรรมตามสูตร Graham Number"),
    "graham_margin_of_safety_pct": ("margin of safety vs Graham Number (%)", "ส่วนเผื่อความปลอดภัยเทียบ Graham Number (%)"),
    "dcf_fair_value": ("fair value from Discounted Cash Flow model", "มูลค่ายุติธรรมจากแบบจำลอง DCF"),
    "dcf_margin_of_safety_pct": ("margin of safety vs DCF fair value (%)", "ส่วนเผื่อความปลอดภัยเทียบมูลค่า DCF (%)"),
    # composite ranking scores
    "score_quality": ("composite Quality score (percentile rank)", "คะแนนรวมด้านคุณภาพ (Quality Score)"),
    "score_growth": ("composite Growth score (percentile rank)", "คะแนนรวมด้านการเติบโต (Growth Score)"),
    "score_value": ("composite Value score (percentile rank)", "คะแนนรวมด้านมูลค่า (Value Score)"),
    "score_momentum": ("composite Momentum score (percentile rank)", "คะแนนรวมด้านโมเมนตัม (Momentum Score)"),
    "score_risk": ("composite Risk score (percentile rank, higher = lower risk)", "คะแนนรวมด้านความเสี่ยง (สูง = เสี่ยงต่ำ)"),
    "score_overall": ("composite Overall ranking score", "คะแนนรวมทั้งหมด (Overall Score)"),
    # classification
    "market": ("market/exchange grouping", "กลุ่มตลาดหลักทรัพย์"),
    "asset_type": ("asset type (equity, etf, index, ...)", "ประเภทสินทรัพย์ (หุ้น, กองทุน ETF, ดัชนี ฯลฯ)"),
    "sector": ("Yahoo Finance sector classification", "หมวดธุรกิจตามการจัดกลุ่มของ Yahoo Finance"),
    "industry": ("industry classification", "หมวดอุตสาหกรรม"),
    "country": ("country of listing/incorporation", "ประเทศที่จดทะเบียน/จดทะเบียนบริษัท"),
    "exchange": ("stock exchange name", "ชื่อตลาดหลักทรัพย์"),
}

OPERATOR_WORDS = {
    "en": {">": "greater than", ">=": "greater than or equal to", "<": "less than", "<=": "less than or equal to", "=": "equal to", "!=": "not equal to"},
    "th": {">": "มากกว่า", ">=": "มากกว่าหรือเท่ากับ", "<": "น้อยกว่า", "<=": "น้อยกว่าหรือเท่ากับ", "=": "เท่ากับ", "!=": "ไม่เท่ากับ"},
}


def _field_label(field: str, lang: str) -> str:
    entry = FIELD_DESCRIPTIONS.get(field)
    if entry is None:
        return field
    return entry[0] if lang == "en" else entry[1]


def _comparison_sentence(comparison: Comparison, lang: str) -> str:
    left_label = _field_label(comparison.left, lang)
    op_word = OPERATOR_WORDS[lang][comparison.operator]
    right = comparison.right
    if isinstance(right, str) and right in FIELD_DESCRIPTIONS:
        right_label = _field_label(right, lang)
    elif isinstance(right, str):
        right_label = f'"{right}"'
    else:
        right_label = str(right)
    if lang == "en":
        return f"{left_label} ({comparison.left}) is {op_word} {right_label}"
    return f"{left_label} ({comparison.left}) {op_word} {right_label}"


def explain_formula(source: str, lang: str = "en") -> str:
    """Turn a formula source string into a plain-language explanation.

    Purely deterministic (regex/dataclass-based via the existing parser) — no LLM call,
    so this always works even when no AI provider is configured.
    """
    formula = parse_formula(source)
    return _explain_parsed(formula, lang)


def _explain_parsed(formula: Formula, lang: str) -> str:
    parts = [_comparison_sentence(formula.first, lang)]
    joiner_words = {"AND": {"en": "and", "th": "และ"}, "OR": {"en": "or", "th": "หรือ"}}
    for joiner, comparison in formula.rest:
        word = joiner_words[joiner][lang]
        parts.append(f"{word} {_comparison_sentence(comparison, lang)}")
    sentence = " ".join(parts)
    if lang == "en":
        return f"This screens for stocks where {sentence}."
    return f"สูตรนี้จะคัดกรองหุ้นที่ {sentence}"


@dataclass(frozen=True)
class DebugResult:
    is_valid: bool
    message: str
    suggestions: tuple[str, ...] = ()


def debug_formula(source: str, lang: str = "en") -> DebugResult:
    """Validate a formula and give actionable suggestions when it fails to parse.

    Deterministic, no LLM required. Catches ParseError from the real parser and adds
    typo detection against known field names via difflib, plus a couple of common
    mistake checks (unsupported parentheses grouping, missing quotes for text values).
    """
    try:
        formula = parse_formula(source)
    except ParseError as exc:
        suggestions = _suggest_fixes(source, str(exc), lang)
        message = (
            f"Could not parse formula: {exc}" if lang == "en" else f"ไม่สามารถแปลงสูตรได้: {exc}"
        )
        return DebugResult(is_valid=False, message=message, suggestions=suggestions)

    unknown_left, unknown_right = _unknown_fields(formula)
    if unknown_left or unknown_right:
        suggestions = []
        for field in unknown_left:
            close = difflib.get_close_matches(field, FIELD_DESCRIPTIONS.keys(), n=1)
            if close:
                suggestions.append(
                    f"'{field}' is not a known field. Did you mean '{close[0]}'?"
                    if lang == "en"
                    else f"'{field}' ไม่ใช่ชื่อฟิลด์ที่รู้จัก หมายถึง '{close[0]}' หรือไม่?"
                )
            else:
                suggestions.append(
                    f"'{field}' is not a known field name." if lang == "en" else f"'{field}' ไม่ใช่ชื่อฟิลด์ที่รู้จัก"
                )
        for value in unknown_right:
            close = difflib.get_close_matches(value, FIELD_DESCRIPTIONS.keys(), n=1)
            if close:
                suggestions.append(
                    f"'{value}' on the right side is not a known field, and is not quoted as text either. "
                    f"Did you mean the field '{close[0]}', or a quoted text value like \"{value}\"?"
                    if lang == "en"
                    else f"'{value}' ทางด้านขวาไม่ใช่ฟิลด์ที่รู้จักและไม่ได้ใส่เครื่องหมายคำพูด "
                    f"หมายถึงฟิลด์ '{close[0]}' หรือค่าข้อความ \"{value}\" หรือไม่?"
                )
            else:
                suggestions.append(
                    f"'{value}' on the right side is unquoted and not a known field. If it's meant to be text, wrap it in double quotes: \"{value}\"."
                    if lang == "en"
                    else f"'{value}' ทางด้านขวาไม่ได้ใส่เครื่องหมายคำพูดและไม่ใช่ฟิลด์ที่รู้จัก หากต้องการให้เป็นข้อความ ให้ใส่เครื่องหมายคำพูดคู่ครอบ: \"{value}\""
                )
        message = (
            "Formula parses but uses unrecognized field name(s)."
            if lang == "en"
            else "สูตรถูกต้องตามไวยากรณ์ แต่มีชื่อฟิลด์ที่ไม่รู้จัก"
        )
        return DebugResult(is_valid=False, message=message, suggestions=tuple(suggestions))

    message = "Formula is valid." if lang == "en" else "สูตรถูกต้อง"
    return DebugResult(is_valid=True, message=message, suggestions=(_explain_parsed(formula, lang),))


def _unknown_fields(formula: Formula) -> tuple[list[str], list[str]]:
    """Return (unknown_left_fields, unknown_bare_right_identifiers)."""
    unknown_left: list[str] = []
    unknown_right: list[str] = []
    comparisons = [formula.first] + [c for _, c in formula.rest]
    for comparison in comparisons:
        if comparison.left not in FIELD_DESCRIPTIONS:
            unknown_left.append(comparison.left)
        right = comparison.right
        if isinstance(right, str) and right not in FIELD_DESCRIPTIONS:
            unknown_right.append(right)
    return unknown_left, unknown_right


def _suggest_fixes(source: str, error_message: str, lang: str) -> tuple[str, ...]:
    suggestions: list[str] = []
    if "(" in source or ")" in source:
        suggestions.append(
            "This formula language does not support parentheses for grouping — write conditions as a flat AND/OR chain instead."
            if lang == "en"
            else "สูตรนี้ไม่รองรับวงเล็บสำหรับจัดกลุ่มเงื่อนไข ให้เขียนเป็นลำดับ AND/OR แบบเรียงต่อกันแทน"
        )
    if re.search(r'(=|!=)\s*[A-Za-z][A-Za-z0-9_]*\s+[A-Za-z][A-Za-z0-9_]*', source) and '"' not in source:
        suggestions.append(
            'Text values (like sector or country names) must be wrapped in double quotes, e.g. sector = "Technology".'
            if lang == "en"
            else 'ค่าที่เป็นข้อความ (เช่น sector หรือ country) ต้องใส่เครื่องหมายคำพูดคู่ครอบ เช่น sector = "Technology"'
        )
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", source)
    known = set(FIELD_DESCRIPTIONS.keys()) | {"AND", "OR"}
    for token in tokens:
        if token.upper() in {"AND", "OR"}:
            continue
        if token not in FIELD_DESCRIPTIONS:
            close = difflib.get_close_matches(token, FIELD_DESCRIPTIONS.keys(), n=1)
            if close:
                suggestions.append(
                    f"'{token}' is not a known field. Did you mean '{close[0]}'?"
                    if lang == "en"
                    else f"'{token}' ไม่ใช่ชื่อฟิลด์ที่รู้จัก หมายถึง '{close[0]}' หรือไม่?"
                )
    if not suggestions:
        suggestions.append(
            f"Check the syntax near the error: {error_message}"
            if lang == "en"
            else f"ตรวจสอบไวยากรณ์บริเวณจุดที่ผิดพลาด: {error_message}"
        )
    return tuple(dict.fromkeys(suggestions))

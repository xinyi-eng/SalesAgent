"""
Report PDF generator using reportlab.

Produces a Chinese-language PDF of a single practice session. Layout:
1. Header (SalesAgent logo + title + scenario + customer type)
2. Score summary (overall + 4 SPIN sub-scores as a horizontal bar chart)
3. Strengths / Improvements / Next focus
4. Knowledge base references (RAG)
5. (Optional) raw evaluation excerpt

Chinese font: simhei.ttf (Windows system font, ships with Win10+).
"""
import io
import os
from typing import Dict, Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)

# Use Windows-shipped SimHei for Chinese rendering.
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",  # Microsoft YaHei (TTC may not work with TTFont)
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
_FONT_REGISTERED = False
_FONT_NAME = "Helvetica"  # fallback


def _register_chinese_font() -> str:
    global _FONT_REGISTERED, _FONT_NAME
    if _FONT_REGISTERED:
        return _FONT_NAME
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                # Use subfont index 0 for .ttc files
                pdfmetrics.registerFont(TTFont("AppCJK", path, subfontIndex=0))
                _FONT_NAME = "AppCJK"
                _FONT_REGISTERED = True
                return _FONT_NAME
            except Exception:
                # Try without subfont index
                try:
                    pdfmetrics.registerFont(TTFont("AppCJK", path))
                    _FONT_NAME = "AppCJK"
                    _FONT_REGISTERED = True
                    return _FONT_NAME
                except Exception:
                    continue
    return _FONT_NAME


def _styles() -> Dict[str, ParagraphStyle]:
    font = _register_chinese_font()
    title = ParagraphStyle(
        "Title", fontName=font, fontSize=22, leading=28,
        textColor=colors.HexColor("#1E293B"), spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        "Subtitle", fontName=font, fontSize=11, leading=15,
        textColor=colors.HexColor("#64748B"), spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "H2", fontName=font, fontSize=14, leading=20,
        textColor=colors.HexColor("#2563EB"), spaceBefore=12, spaceAfter=6,
    )
    body = ParagraphStyle(
        "Body", fontName=font, fontSize=10, leading=15,
        textColor=colors.HexColor("#1E293B"), spaceAfter=4,
    )
    small = ParagraphStyle(
        "Small", fontName=font, fontSize=9, leading=13,
        textColor=colors.HexColor("#475569"), spaceAfter=2,
    )
    return {"title": title, "subtitle": subtitle, "h2": h2, "body": body, "small": small}


def _score_bar(label: str, score: int) -> Table:
    """A small two-row table: label + score, with a colored bar.
    `score` is 0-100.
    """
    font = _register_chinese_font()
    # Bar width proportional to score (max 10cm)
    full_w = 10 * cm
    bar_w = full_w * max(0, min(100, score)) / 100
    # Color by score
    if score >= 80:
        bar_color = colors.HexColor("#10B981")
    elif score >= 60:
        bar_color = colors.HexColor("#3B82F6")
    elif score >= 40:
        bar_color = colors.HexColor("#F59E0B")
    else:
        bar_color = colors.HexColor("#EF4444")
    bar = Table(
        [[""]],
        colWidths=[bar_w],
        rowHeights=[6 * mm],
    )
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bar_color),
        ("LINEABOVE", (0, 0), (-1, 0), 0, colors.white),
        ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),
    ]))
    track = Table(
        [[""]],
        colWidths=[full_w],
        rowHeights=[6 * mm],
    )
    track.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E2E8F0")),
    ]))
    # Compose label row + bar row in one table
    lbl_para = Paragraph(f"<b>{label}</b>", ParagraphStyle("lbl", fontName=font, fontSize=10))
    score_para = Paragraph(
        f"<b>{score}</b>/100",
        ParagraphStyle("score", fontName=font, fontSize=11, alignment=2),
    )
    container = Table(
        [[lbl_para, score_para]],
        colWidths=[8 * cm, 2 * cm],
    )
    container.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    bar_under_track = Table(
        [[bar], [track]],
        colWidths=[full_w],
    )
    bar_under_track.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    out = Table(
        [[container], [bar_under_track]],
        colWidths=[10 * cm + 2 * cm],
    )
    out.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return out


def _kv_table(rows: List[List[str]]) -> Table:
    font = _register_chinese_font()
    t = Table(
        [[Paragraph(f"<b>{k}</b>", ParagraphStyle("k", fontName=font, fontSize=10)),
          Paragraph(v, ParagraphStyle("v", fontName=font, fontSize=10))] for k, v in rows],
        colWidths=[3 * cm, 14 * cm],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
    ]))
    return t


def _bullet_items(items: List[str]) -> Table:
    font = _register_chinese_font()
    style = ParagraphStyle("li", fontName=font, fontSize=10, leading=15,
                          leftIndent=10, bulletIndent=2)
    rows = []
    for it in items:
        if not it:
            continue
        rows.append([Paragraph(f"• {it}", style)])
    t = Table(rows, colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _ref_card(ref: Dict[str, Any], idx: int) -> KeepTogether:
    font = _register_chinese_font()
    s = _styles()
    src = ref.get("source", "知识库")
    chapter = ref.get("chapter", "")
    section = ref.get("section", "")
    header = f"<b>[{idx}] {src}</b>"
    if chapter:
        header += f"  ·  <i>{chapter}</i>"
    if section:
        header += f"  ·  <i>{section}</i>"
    relevance = ref.get("relevance")
    rel_str = f"  ·  相关度 {(relevance * 100):.0f}%" if relevance is not None else ""
    excerpt = (ref.get("excerpt") or "").replace("\n", " ").strip()
    if len(excerpt) > 320:
        excerpt = excerpt[:320] + "…"
    body_html = (
        f"{header}<br/>"
        f"<font color='#64748B' size='9'>"
        f"分类: {ref.get('category', '-')}{rel_str}</font><br/>"
        f"{excerpt}"
    )
    p = Paragraph(body_html, ParagraphStyle(
        "ref", parent=s["body"], fontSize=10, leading=15,
        textColor=colors.HexColor("#1E293B"),
    ))
    t = Table([[p]], colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#7C3AED")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([t, Spacer(1, 4 * mm)])


def render_report_pdf(summary: Dict[str, Any]) -> bytes:
    """Build the report PDF and return its raw bytes."""
    font = _register_chinese_font()
    s = _styles()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title="SalesAgent 对练报告",
        author="SalesAgent",
    )

    story = []
    # --- Header ---
    scenario_name = summary.get("scenario_name", "")
    role = summary.get("role_config") or {}
    personality_map = {
        "rational": "理性型", "emotional": "感性型",
        "hesitant": "犹豫型", "decisive": "果断型",
    }
    position_map = {
        "junior": "初级客户经理", "middle": "中级采购经理", "senior": "高级总监",
    }
    sub = []
    if scenario_name:
        sub.append(f"场景: {scenario_name}")
    sub.append(f"客户类型: {position_map.get(role.get('position_level', ''), '-')} · "
               f"{personality_map.get(role.get('personality', ''), '-')} · "
               f"{role.get('decision_style', '-')}")
    sub.append(f"会话ID: {summary.get('session_id', '-')}")
    story.append(Paragraph("SalesAgent 对练报告", s["title"]))
    story.append(Paragraph(" · ".join(sub), s["subtitle"]))

    # --- Overall score (big) ---
    overall = summary.get("overall_score", 0)
    big_score = Table(
        [[
            Paragraph(
                f'<font color="#2563EB" size="40"><b>{overall}</b></font>'
                f'<font color="#64748B" size="14"> / 100</font>',
                ParagraphStyle("bs_num", fontName=font, alignment=0)
            ),
            Paragraph("综合评分<br/><font size='8' color='#94A3B8'>OVERALL SCORE</font>",
                       ParagraphStyle("bs_lbl", fontName=font, fontSize=10, alignment=0,
                                     textColor=colors.HexColor("#64748B"))),
        ]],
        colWidths=[5 * cm, 12 * cm],
    )
    big_score.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(big_score)
    story.append(Spacer(1, 6 * mm))

    # --- SPIN sub-scores ---
    story.append(Paragraph("SPIN 四维评分", s["h2"]))
    story.append(_score_bar("S - Situation 背景", summary.get("situation_score", 0)))
    story.append(_score_bar("P - Problem 难点", summary.get("problem_score", 0)))
    story.append(_score_bar("I - Implication 暗示", summary.get("implication_score", 0)))
    story.append(_score_bar("N - Need-payoff 需求效益", summary.get("need_payoff_score", 0)))
    story.append(Spacer(1, 6 * mm))

    # --- Strengths / Improvements / Next focus ---
    story.append(Paragraph("做得好的点", s["h2"]))
    story.append(_bullet_items(summary.get("key_strengths") or ["暂无"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("需要改进的点", s["h2"]))
    story.append(_bullet_items(summary.get("areas_for_improvement") or ["暂无"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("下次练习重点", s["h2"]))
    story.append(Paragraph(summary.get("next_practice_focus") or "继续练习，提升SPIN技能", s["body"]))
    story.append(Spacer(1, 6 * mm))

    # --- Knowledge base references (RAG) ---
    refs = summary.get("knowledge_refs") or []
    if refs:
        story.append(Paragraph(
            f"AI 客户的话术依据 ({len(refs)} 条)", s["h2"]))
        story.append(Paragraph(
            "本场对练中 AI 客户引用的销售知识库条目（依据相关度排序）。"
            "您可以据此理解 AI 的提问逻辑，针对性准备下一次练习。",
            s["small"]
        ))
        story.append(Spacer(1, 2 * mm))
        for i, ref in enumerate(refs, 1):
            story.append(_ref_card(ref, i))
        story.append(Spacer(1, 4 * mm))

    # --- AI 教练详细评语 (raw evaluation excerpt) ---
    raw_eval = summary.get("raw_evaluation", "").strip()
    if raw_eval:
        story.append(Paragraph("AI 教练详细评语", s["h2"]))
        story.append(Paragraph(
            raw_eval.replace("\n", "<br/>"),
            ParagraphStyle("raw", parent=s["body"], fontSize=9, leading=13,
                          textColor=colors.HexColor("#334155"))
        ))

    # --- Footer ---
    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.drawString(
            2 * cm, 1 * cm,
            "SalesAgent · 本报告由 AI 教练基于知识库生成"
        )
        canvas.drawCentredString(
            A4[0] / 2, 1 * cm,
            f"Session: {summary.get('session_id', '')[:8]}"
        )
        canvas.drawRightString(
            A4[0] - 2 * cm, 1 * cm,
            f"第 {doc_.page} 页"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buffer.seek(0)
    return buffer.getvalue()

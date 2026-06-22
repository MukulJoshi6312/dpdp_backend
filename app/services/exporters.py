"""Generate downloadable PDF and XML representations of a law.

XML uses only the stdlib. PDF uses reportlab if available; if reportlab is not
installed the PDF endpoint returns a clear 503 instead of crashing the server.
"""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from app.schemas.law import Law


# --- XML (LegalDocML-ish) -------------------------------------------------

def law_to_xml(law: Law) -> bytes:
    """Render a law as a structured XML document (simplified LegalDocML)."""
    lines: list = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(
        '<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">'
    )
    lines.append("  <act>")
    lines.append("    <meta>")
    lines.append(f"      <id>{escape(law.id)}</id>")
    lines.append(f"      <title>{escape(law.title)}</title>")
    lines.append(f"      <year>{law.year}</year>")
    lines.append(f"      <category>{escape(law.category)}</category>")
    lines.append(f"      <authority>{escape(law.authority)}</authority>")
    lines.append(f"      <status>{escape(law.status)}</status>")
    lines.append(f"      <sections>{law.sections}</sections>")
    lines.append(f"      <lastUpdated>{escape(law.lastUpdated)}</lastUpdated>")
    lines.append("    </meta>")

    lines.append("    <body>")
    for p in law.provisions:
        lines.append(f'      <provision num="{escape(p.num)}">')
        lines.append(f"        <heading>{escape(p.title)}</heading>")
        lines.append(f"        <content>{escape(p.text)}</content>")
        if p.rules:
            lines.append("        <rules>")
            for r in p.rules:
                lines.append(f"          <rule>{escape(r)}</rule>")
            lines.append("        </rules>")
        lines.append("      </provision>")
    lines.append("    </body>")

    if law.penalties:
        lines.append("    <penalties>")
        for pen in law.penalties:
            lines.append(
                f'      <penalty breach="{escape(pen.breach)}" '
                f'max="{pen.max}" unit="{escape(pen.unit)}"/>'
            )
        lines.append("    </penalties>")

    lines.append("  </act>")
    lines.append("</akomaNtoso>")
    return ("\n".join(lines)).encode("utf-8")


# --- PDF ------------------------------------------------------------------

def reportlab_available() -> bool:
    try:
        import reportlab  # noqa: F401
        return True
    except ImportError:
        return False


def law_to_pdf(law: Law) -> bytes:
    """Render a law as a simple, readable PDF. Requires reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib import colors

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"{law.title}, {law.year}",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=18, leading=22)
    meta = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=12)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=2)

    story: list = []
    story.append(Paragraph(f"{escape(law.title)}, {law.year}", h1))
    story.append(
        Paragraph(
            f"{escape(law.authority)} &nbsp;·&nbsp; {escape(law.category)} "
            f"&nbsp;·&nbsp; {escape(law.status)} &nbsp;·&nbsp; "
            f"{law.sections} sections &nbsp;·&nbsp; updated {escape(law.lastUpdated)}",
            meta,
        )
    )
    story.append(Spacer(1, 6))
    story.append(Paragraph(escape(law.shortDesc), body))

    # Provisions
    if law.provisions:
        story.append(Paragraph("Provisions", h2))
        for p in law.provisions:
            story.append(Paragraph(f"<b>{escape(p.num)} — {escape(p.title)}</b>", body))
            if p.text:
                story.append(Paragraph(escape(p.text), body))
            for r in p.rules:
                story.append(Paragraph(f"• {escape(r)}", bullet))
            story.append(Spacer(1, 6))

    # Penalties
    if law.penalties:
        story.append(Paragraph("Penalty schedule", h2))
        data = [["Breach", "Max", "Unit"]]
        for pen in law.penalties:
            data.append([pen.breach, str(pen.max), pen.unit])
        tbl = Table(data, colWidths=[110 * mm, 25 * mm, 25 * mm])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ]
            )
        )
        story.append(tbl)

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Generated by Nyaykosh — informational copy, not the official gazette.",
            meta,
        )
    )

    doc.build(story)
    return buf.getvalue()

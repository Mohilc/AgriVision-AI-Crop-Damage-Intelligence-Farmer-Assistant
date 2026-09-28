"""
AgriVision - Report Generator Module
Formats farmer-friendly text reports for Telegram and generates downloadable PDF reports.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def format_telegram_report(data: Dict[str, Any]) -> str:
    """
    Formats the structured AI analysis into the clean, farmer-friendly Telegram message format.
    """
    crop = data.get("crop_identified", "Unknown Crop")
    damage_str = "Detected" if data.get("damage_detected", False) else "None / Healthy"
    cause = data.get("possible_cause", "Uncertain — image evidence is insufficient.")
    severity = data.get("severity", "None")
    est_damage = data.get("estimated_visible_damage_percentage", "Not estimated")
    
    # Severity icon
    sev_icons = {
        "None": "🟢",
        "Low": "🟡",
        "Moderate": "🟠",
        "High": "🔴",
        "Severe": "🚨"
    }
    sev_icon = sev_icons.get(severity, "ℹ️")

    # Format affected regions
    regions = data.get("affected_regions", [])
    regions_str = ", ".join(regions) if isinstance(regions, list) and regions else "Entire frame"

    # Format symptoms list
    symptoms = data.get("visible_symptoms", [])
    if isinstance(symptoms, list) and symptoms:
        symptoms_str = "\n".join([f"• {s}" for s in symptoms])
    else:
        symptoms_str = "• No acute symptoms observed"

    # Format recommended steps
    steps = data.get("recommended_next_steps", [])
    if isinstance(steps, list) and steps:
        steps_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])
    else:
        steps_str = "1. Monitor field regularly.\n2. Consult local agricultural officer if conditions change."

    # Format conditions for damage occurrence
    conditions = data.get("conditions_favoring_damage")
    if conditions:
        conditions_block = f"\n*Conditions for damage occurrence:*\n{conditions}\n"
    else:
        conditions_block = ""

    # Format solutions & practical remedies
    solutions = data.get("solutions_and_remedies", [])
    if isinstance(solutions, list) and solutions:
        solutions_block = "\n*Solutions & practical remedies:*\n" + "\n".join([f"• {s}" for s in solutions]) + "\n"
    elif isinstance(solutions, str) and solutions.strip():
        solutions_block = f"\n*Solutions & practical remedies:*\n{solutions}\n"
    else:
        solutions_block = ""

    msg = f"""🌱 *AGRIVISION REPORT*

*Crop:*
{crop}

*Damage:*
{damage_str}

*Possible cause:*
{cause}
{conditions_block}{solutions_block}
*Severity:*
{sev_icon} {severity}

*Estimated visible damage:*
{est_damage}

*Affected region:*
{regions_str}

*Visible symptoms:*
{symptoms_str}

*Recommended next steps:*
{steps_str}

⚠️ *Note:*
This is an AI-based visual assessment and should be treated as an initial screening, not a definitive diagnosis. Always verify with local agricultural experts (e.g., Krishi Bhavan)."""

    # If crop is unknown, prompt user to clarify crop name
    if str(crop).strip().lower() in ["unknown", "unknown crop", "unidentified", "uncertain", "none"]:
        msg += """

❓ *Crop Unidentified:*
The AI detected visible symptoms, but the crop name could not be confirmed with certainty from this angle.

👉 *Please reply with your crop name* (e.g., _Rose, Tomato, Cotton, Wheat, Rice, Chilli_).
I will immediately report:
🌧️ *Conditions* causing this damage to occur
🛠️ *Tailored Remedies & Practical Solutions* for your specific crop!"""

    return msg


def format_history_item(analysis: Dict[str, Any], index: int) -> str:
    """
    Formats a single item for the /history command.
    Example: 1. Tomato — Moderate — 20–30% — 28 Sept 2026
    """
    crop = analysis.get("crop_identified", "Crop")
    severity = analysis.get("severity", "N/A")
    damage = analysis.get("estimated_visible_damage_percentage", "N/A")
    ts = analysis.get("timestamp", "")
    
    try:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        date_str = dt.strftime("%d %b %Y")
    except Exception:
        date_str = ts or "Recent"

    return f"{index}. *{crop}* — {severity} — {damage} — _{date_str}_"


def generate_pdf_report(
    data: Dict[str, Any],
    output_pdf_path: str,
    image_path: Optional[str] = None
) -> str:
    """
    Generates a professional, printable PDF assessment report for the farmer/evaluator.
    """
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1B5E20"),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#4E6E58"),
        spaceAfter=12
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2E7D32"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1C2D27")
    )
    alert_style = ParagraphStyle(
        'AlertText',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#7F4B00")
    )

    story = []

    # Header
    story.append(Paragraph("AgriVision — Crop Damage Assessment Report", title_style))
    date_str = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    story.append(Paragraph(f"AI Agricultural Screening Report • Generated on: {date_str}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2E7D32"), spaceAfter=14))

    # Core Assessment Table
    crop = data.get("crop_identified", "Unknown")
    damage_det = "Detected" if data.get("damage_detected") else "None (Healthy)"
    cause = data.get("possible_cause", "Uncertain")
    severity = data.get("severity", "None")
    est_dmg = data.get("estimated_visible_damage_percentage", "Not estimated")
    confidence = data.get("confidence", "Medium")
    
    table_data = [
        [Paragraph("<b>Crop Identified:</b>", body_style), Paragraph(str(crop), body_style),
         Paragraph("<b>Damage Status:</b>", body_style), Paragraph(str(damage_det), body_style)],
        [Paragraph("<b>Severity Level:</b>", body_style), Paragraph(str(severity), body_style),
         Paragraph("<b>Est. Visible Damage:</b>", body_style), Paragraph(str(est_dmg), body_style)],
        [Paragraph("<b>Possible Cause:</b>", body_style), Paragraph(str(cause), body_style),
         Paragraph("<b>Visual Confidence:</b>", body_style), Paragraph(str(confidence), body_style)],
    ]

    t = Table(table_data, colWidths=[1.5*inch, 2.0*inch, 1.5*inch, 2.2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F4F7F4")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#C8D8C8")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Image (if available and valid)
    if image_path and os.path.exists(image_path):
        try:
            img = RLImage(image_path, width=3.2*inch, height=2.4*inch)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 10))
        except Exception:
            pass

    # Visible Symptoms & Affected Regions
    story.append(Paragraph("Visual Diagnostics & Localization", section_heading))
    symptoms = data.get("visible_symptoms", [])
    regions = data.get("affected_regions", [])
    
    sym_html = "<br/>".join([f"• {s}" for s in symptoms]) if symptoms else "• No acute symptoms recorded"
    reg_html = "<br/>".join([f"• {r}" for r in regions]) if regions else "• Entire frame"
    
    diag_table = [
        [Paragraph("<b>Visible Symptoms:</b>", body_style), Paragraph("<b>Affected Image Regions:</b>", body_style)],
        [Paragraph(sym_html, body_style), Paragraph(reg_html, body_style)]
    ]
    dt_table = Table(diag_table, colWidths=[3.6*inch, 3.6*inch])
    dt_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E8EFE8")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0DDD0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(dt_table)
    story.append(Spacer(1, 10))

    # Recommended Next Steps
    story.append(Paragraph("Recommended Farmer Action Plan", section_heading))
    steps = data.get("recommended_next_steps", [])
    if steps:
        steps_table_data = [[Paragraph(f"<b>{i+1}.</b>", body_style), Paragraph(step, body_style)] for i, step in enumerate(steps)]
        st_table = Table(steps_table_data, colWidths=[0.4*inch, 6.8*inch])
        st_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(st_table)
    else:
        story.append(Paragraph("• Standard crop monitoring advised.", body_style))

    story.append(Spacer(1, 12))

    # Limitations & Disclaimer
    disclaimer_box = [
        [Paragraph("<b>⚠️ AI Screening Disclaimer & Limitations:</b>", alert_style)],
        [Paragraph(
            "This report is generated by an artificial intelligence vision screening prototype. "
            "Estimates are approximate visual observations and must not be used as the sole basis for high-cost chemical interventions. "
            "Always consult your local Krishi Bhavan or certified agricultural extension officer.", alert_style)]
    ]
    disc_table = Table(disclaimer_box, colWidths=[7.2*inch])
    disc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FFF8E1")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#FFE082")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(disc_table)

    # Build PDF
    doc.build(story)
    return output_pdf_path

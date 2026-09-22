import io
import json
import datetime
from typing import Dict, Any, List
from app.services.audio_processor import format_timestamp

def generate_markdown_mom(meeting_dict: Dict[str, Any]) -> str:
    """Generate structured Minutes of Meeting in GitHub-flavored Markdown."""
    title = meeting_dict.get("title", "Meeting Minutes")
    meeting_date = meeting_dict.get("meeting_date")
    if isinstance(meeting_date, datetime.datetime):
        date_str = meeting_date.strftime("%B %d, %Y - %H:%M UTC")
    else:
        date_str = str(meeting_date or "N/A")

    duration = format_timestamp(meeting_dict.get("duration_seconds", 0.0))
    speakers = [s.get("display_name") or s.get("speaker_label", "Speaker") for s in meeting_dict.get("speakers", [])]
    participants_str = ", ".join(speakers) if speakers else "Not specified"

    summary_obj = meeting_dict.get("summary") or {}
    exec_summary = summary_obj.get("executive_summary", "No executive summary available.")
    agenda_topics = summary_obj.get("agenda_topics", [])

    lines = []
    lines.append(f"# Minutes of Meeting: {title}")
    lines.append("")
    lines.append(f"**Date & Time:** {date_str}  ")
    lines.append(f"**Duration:** {duration}  ")
    lines.append(f"**Participants:** {participants_str}  ")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Executive Summary")
    lines.append(exec_summary)
    lines.append("")

    if agenda_topics:
        lines.append("## 2. Agenda & Topics Discussed")
        for topic in agenda_topics:
            lines.append(f"- {topic}")
        lines.append("")

    key_points = meeting_dict.get("key_points", [])
    if key_points:
        lines.append("## 3. Key Discussion Points")
        for kp in key_points:
            cat = f"**[{kp.get('category', 'General')}]** " if kp.get("category") else ""
            ts = f" *({format_timestamp(kp.get('start_time', 0.0))})*" if kp.get("start_time") is not None else ""
            lines.append(f"- {cat}{kp.get('point')}{ts}")
        lines.append("")

    decisions = meeting_dict.get("decisions", [])
    if decisions:
        lines.append("## 4. Key Decisions Reached")
        for idx, dec in enumerate(decisions, 1):
            lines.append(f"### 4.{idx} {dec.get('decision')}")
            if dec.get("context"):
                lines.append(f"- **Context:** {dec.get('context')}")
            if dec.get("impact"):
                lines.append(f"- **Impact:** {dec.get('impact')}")
            if dec.get("source_text"):
                lines.append(f"- **Evidence:** *\"{dec.get('source_text')}\"*")
            lines.append("")

    action_items = meeting_dict.get("action_items", [])
    if action_items:
        lines.append("## 5. Action Items & Commitments")
        lines.append("| Status | Action Item | Assignee | Deadline | Priority |")
        lines.append("|:---:|---|---|---|---|")
        for item in action_items:
            status = "✅ Done" if item.get("is_completed") else "⏳ Pending"
            desc = item.get("description", "").replace("|", "/")
            assignee = item.get("assignee", "Unassigned")
            deadline = item.get("deadline") or "TBD"
            priority = item.get("priority", "Medium")
            lines.append(f"| {status} | {desc} | {assignee} | {deadline} | {priority} |")
        lines.append("")

    important_dates = meeting_dict.get("important_dates", [])
    if important_dates:
        lines.append("## 6. Important Dates & Deadlines")
        for dt in important_dates:
            flag = " *(⚠️ Needs Confirmation)*" if dt.get("needs_confirmation") else ""
            norm = f" ({dt.get('normalized_date')})" if dt.get("normalized_date") else ""
            lines.append(f"- **{dt.get('raw_phrase')}{norm}:** {dt.get('description')}{flag}")
        lines.append("")

    questions = meeting_dict.get("unresolved_questions", [])
    if questions:
        lines.append("## 7. Open & Unresolved Questions")
        for q in questions:
            raised = f" *(Raised by: {q.get('raised_by', 'Unknown')})*"
            lines.append(f"- **Q:** {q.get('question')}{raised}")
            if q.get("context"):
                lines.append(f"  - Context: {q.get('context')}")
        lines.append("")

    takeaways = meeting_dict.get("takeaways", [])
    if takeaways:
        lines.append("## 8. Strategic Takeaways & Next Steps")
        for t in takeaways:
            lines.append(f"- {t.get('takeaway')}")
        lines.append("")

    # Transcript Appendix
    segments = meeting_dict.get("transcript_segments", [])
    if segments:
        lines.append("---")
        lines.append("## Appendix: Complete Transcript")
        lines.append("")
        for seg in segments:
            ts = format_timestamp(seg.get("start_time", 0.0))
            spk = seg.get("speaker_label", "Speaker")
            text = seg.get("cleaned_text") or seg.get("raw_text", "")
            lines.append(f"**[{ts}] {spk}:** {text}  ")
        lines.append("")

    return "\n".join(lines)


def generate_json_mom(meeting_dict: Dict[str, Any]) -> str:
    """Export complete structured meeting data as pretty-printed JSON."""
    return json.dumps(meeting_dict, indent=2, default=str)


def generate_pdf_mom(meeting_dict: Dict[str, Any]) -> bytes:
    """Generate a clean, professional PDF of Meeting Minutes using ReportLab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E293B")
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155")
    )
    bold_body_style = ParagraphStyle(
        'DocBoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B")
    )

    story = []

    # Title & Metadata
    title = meeting_dict.get("title", "Meeting Minutes")
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 6))

    meeting_date = meeting_dict.get("meeting_date")
    date_str = meeting_date.strftime("%B %d, %Y %H:%M UTC") if isinstance(meeting_date, datetime.datetime) else str(meeting_date or "N/A")
    duration = format_timestamp(meeting_dict.get("duration_seconds", 0.0))
    speakers = [s.get("display_name") or s.get("speaker_label", "Speaker") for s in meeting_dict.get("speakers", [])]
    participants_str = ", ".join(speakers) if speakers else "N/A"

    meta_text = f"<b>Date:</b> {date_str} &nbsp;|&nbsp; <b>Duration:</b> {duration} &nbsp;|&nbsp; <b>Participants:</b> {participants_str}"
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=12))

    # Executive Summary
    summary_obj = meeting_dict.get("summary") or {}
    exec_summary = summary_obj.get("executive_summary", "No executive summary available.")
    story.append(Paragraph("1. Executive Summary", h2_style))
    story.append(Paragraph(exec_summary, body_style))
    story.append(Spacer(1, 10))

    # Key Decisions
    decisions = meeting_dict.get("decisions", [])
    if decisions:
        story.append(Paragraph("2. Key Decisions", h2_style))
        for dec in decisions:
            dec_text = f"<b>• {dec.get('decision')}</b>"
            if dec.get('context'):
                dec_text += f"<br/><font color='#64748B'>Context: {dec.get('context')}</font>"
            story.append(Paragraph(dec_text, body_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    # Action Items
    action_items = meeting_dict.get("action_items", [])
    if action_items:
        story.append(Paragraph("3. Action Items", h2_style))
        table_data = [
            [
                Paragraph("<b>Action</b>", bold_body_style),
                Paragraph("<b>Assignee</b>", bold_body_style),
                Paragraph("<b>Deadline</b>", bold_body_style),
                Paragraph("<b>Priority</b>", bold_body_style)
            ]
        ]
        for item in action_items:
            table_data.append([
                Paragraph(item.get("description", ""), body_style),
                Paragraph(item.get("assignee", "Unassigned"), body_style),
                Paragraph(item.get("deadline") or "TBD", body_style),
                Paragraph(item.get("priority", "Medium"), body_style)
            ])

        table = Table(table_data, colWidths=[240, 110, 90, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))

    # Important Dates
    dates = meeting_dict.get("important_dates", [])
    if dates:
        story.append(Paragraph("4. Important Dates & Deadlines", h2_style))
        for dt in dates:
            norm = f" ({dt.get('normalized_date')})" if dt.get("normalized_date") else ""
            flag = " <font color='#D97706'>[Needs Confirmation]</font>" if dt.get("needs_confirmation") else ""
            date_text = f"<b>• {dt.get('raw_phrase')}{norm}:</b> {dt.get('description')}{flag}"
            story.append(Paragraph(date_text, body_style))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 6))

    # Unresolved Questions
    questions = meeting_dict.get("unresolved_questions", [])
    if questions:
        story.append(Paragraph("5. Unresolved Questions", h2_style))
        for q in questions:
            q_text = f"<b>• {q.get('question')}</b> (Raised by: {q.get('raised_by', 'Unknown')})"
            story.append(Paragraph(q_text, body_style))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 6))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

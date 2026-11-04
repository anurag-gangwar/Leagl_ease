import os
from datetime import datetime


REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

SEVERITY_COLORS = {
    'High':   (220, 53, 69),    # Red
    'Medium': (255, 193, 7),    # Yellow
    'Low':    (40, 167, 69),    # Green
}


def generate_pdf_report(contract, clauses) -> str:
    """Generate a PDF report using ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError:
        raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

    filename = f"report_{contract.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#6c757d'),
        spaceAfter=20,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1a1a2e'),
        spaceBefore=20,
        spaceAfter=8,
        fontName='Helvetica-Bold',
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        leading=16,
    )
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#6c757d'),
        spaceAfter=2,
    )

    story = []

    # Header
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("⚖️ Legal-Ease", title_style))
    story.append(Paragraph("AI-Powered Contract Analysis Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a1a2e')))
    story.append(Spacer(1, 0.2*inch))

    # Contract Info Table
    risk_color_map = {
        'High': colors.HexColor('#dc3545'),
        'Medium': colors.HexColor('#ffc107'),
        'Low': colors.HexColor('#28a745'),
        'Unknown': colors.HexColor('#6c757d'),
    }
    risk_bg = risk_color_map.get(contract.risk_score, colors.HexColor('#6c757d'))

    info_data = [
        ['File Name', contract.filename],
        ['Contract Type', contract.contract_type or 'N/A'],
        ['Analysis Language', contract.language.title()],
        ['Date Generated', datetime.now().strftime('%d %B %Y, %I:%M %p')],
        ['Overall Risk', contract.risk_score],
    ]

    info_table = Table(info_data, colWidths=[4*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a1a2e')),
        ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (1, 4), (1, 4), risk_bg),
        ('TEXTCOLOR', (1, 4), (1, 4), colors.white),
        ('FONTNAME', (1, 4), (1, 4), 'Helvetica-Bold'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))

    # Summary Section
    if contract.summary:
        story.append(Paragraph("📋 Contract Summary", heading_style))
        story.append(Paragraph(contract.summary, body_style))

    if contract.translated_summary:
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"🌐 Summary in {contract.language.title()}", heading_style))
        story.append(Paragraph(contract.translated_summary, body_style))

    story.append(Spacer(1, 0.2*inch))

    # Risk Dashboard
    sc = contract.severity_counts()
    story.append(Paragraph("📊 Risk Dashboard", heading_style))

    risk_data = [
        ['Risk Level', 'Count', 'Status'],
        ['🔴 High Risk', str(sc.get('High', 0)), 'Requires Immediate Attention'],
        ['🟡 Medium Risk', str(sc.get('Medium', 0)), 'Review Carefully'],
        ['🟢 Low Risk', str(sc.get('Low', 0)), 'Standard Clauses'],
    ]
    risk_table = Table(risk_data, colWidths=[5*cm, 2.5*cm, 8.5*cm])
    risk_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fff5f5')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fffbf0')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f0fff4')),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    story.append(risk_table)

    # Flagged Clauses
    story.append(PageBreak())
    story.append(Paragraph("🚩 Analyzed Clauses", heading_style))

    for i, clause in enumerate(clauses, 1):
        sc_color = risk_color_map.get(clause.severity, colors.HexColor('#6c757d'))

        clause_header = Table(
            [[f"#{i} — {clause.clause_type or 'Clause'}", clause.severity]],
            colWidths=[13*cm, 3*cm]
        )
        clause_header.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('BACKGROUND', (1, 0), (1, 0), sc_color),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ]))
        story.append(clause_header)

        clause_body_data = []
        if clause.simplified_text:
            clause_body_data.append(['📝 Plain English', clause.simplified_text])
        if clause.translated_text:
            clause_body_data.append([f'🌐 {contract.language.title()}', clause.translated_text])
        if clause.explanation:
            clause_body_data.append(['⚠️ Real-World Risk', clause.explanation])

        if clause_body_data:
            clause_body = Table(clause_body_data, colWidths=[3.5*cm, 12.5*cm])
            clause_body.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('PADDING', (0, 0), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (1, 0), (1, -1),
                 [colors.white, colors.HexColor('#fdfdfd'), colors.HexColor('#fff8e1')]),
            ]))
            story.append(clause_body)

        story.append(Spacer(1, 0.2*inch))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dee2e6')))
    story.append(Spacer(1, 0.1*inch))
    footer_text = (
        "Generated by Legal-Ease — AI Contract Analyzer for Regional Indian Languages. "
        "This report is for informational purposes only and does not constitute legal advice. "
        "Please consult a qualified lawyer for legal decisions."
    )
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#aaa'), alignment=TA_CENTER
    )))

    doc.build(story)
    return filepath


def generate_docx_report(contract, clauses) -> str:
    """Generate a DOCX report using python-docx."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor, Inches, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        raise RuntimeError("python-docx is not installed. Run: pip install python-docx")

    filename = f"report_{contract.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    # Title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run('⚖️ Legal-Ease — Contract Analysis Report')
    run.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = RGBColor(0x1a, 0x1a, 0x2e)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run(f'Generated on {datetime.now().strftime("%d %B %Y")}').font.color.rgb = RGBColor(0x6c, 0x75, 0x7d)

    doc.add_paragraph()

    # Contract Info
    doc.add_heading('Contract Details', level=2)
    info = {
        'File Name':         contract.filename,
        'Contract Type':     contract.contract_type or 'N/A',
        'Language':          contract.language.title(),
        'Overall Risk':      contract.risk_score,
    }
    table = doc.add_table(rows=len(info), cols=2)
    table.style = 'Table Grid'
    for i, (k, v) in enumerate(info.items()):
        table.rows[i].cells[0].text = k
        table.rows[i].cells[1].text = v
        table.rows[i].cells[0].paragraphs[0].runs[0].bold = True
    doc.add_paragraph()

    # Summary
    if contract.summary:
        doc.add_heading('📋 Contract Summary (English)', level=2)
        doc.add_paragraph(contract.summary)

    if contract.translated_summary:
        doc.add_heading(f'🌐 Summary in {contract.language.title()}', level=2)
        doc.add_paragraph(contract.translated_summary)

    # Risk counts
    sc = contract.severity_counts()
    doc.add_heading('📊 Risk Overview', level=2)
    risk_table = doc.add_table(rows=4, cols=2)
    risk_table.style = 'Table Grid'
    risk_table.rows[0].cells[0].text = 'Risk Level'
    risk_table.rows[0].cells[1].text = 'Count'
    risk_table.rows[1].cells[0].text = '🔴 High'
    risk_table.rows[1].cells[1].text = str(sc.get('High', 0))
    risk_table.rows[2].cells[0].text = '🟡 Medium'
    risk_table.rows[2].cells[1].text = str(sc.get('Medium', 0))
    risk_table.rows[3].cells[0].text = '🟢 Low'
    risk_table.rows[3].cells[1].text = str(sc.get('Low', 0))

    # Clauses
    doc.add_page_break()
    doc.add_heading('🚩 Analyzed Clauses', level=2)

    for i, clause in enumerate(clauses, 1):
        heading = doc.add_heading(
            f'#{i} — {clause.clause_type or "Clause"} [{clause.severity}]', level=3
        )

        if clause.simplified_text:
            p = doc.add_paragraph()
            p.add_run('📝 Plain English: ').bold = True
            p.add_run(clause.simplified_text)

        if clause.translated_text:
            p = doc.add_paragraph()
            p.add_run(f'🌐 {contract.language.title()}: ').bold = True
            p.add_run(clause.translated_text)

        if clause.explanation:
            p = doc.add_paragraph()
            p.add_run('⚠️ Real-World Risk: ').bold = True
            p.add_run(clause.explanation)

        doc.add_paragraph()

    # Footer
    footer_para = doc.add_paragraph()
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_para.add_run(
        'This report is for informational purposes only. Not legal advice.'
    )
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0xaa, 0xaa, 0xaa)

    doc.save(filepath)
    return filepath

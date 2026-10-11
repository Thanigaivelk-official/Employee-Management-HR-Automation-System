import io
from decimal import Decimal
import calendar
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_payslip_pdf(payroll_record):
    """
    Generates a high-quality professional PDF payslip using ReportLab.
    Returns a bytes buffer suitable for Django FileResponse / HttpResponse.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=1 # Center
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        alignment=1
    )

    header_badge_style = ParagraphStyle(
        'HeaderBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e40af'),
        alignment=1
    )

    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    val_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )

    month_name = calendar.month_name[payroll_record.month]

    # Organization Header
    story.append(Paragraph("EMPLOYEE MANAGEMENT &amp; HR AUTOMATION SYSTEM", title_style))
    story.append(Paragraph("Corporate Human Resources Department | Confidential Payslip", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e40af'), spaceAfter=15))

    # Pay Period Banner
    story.append(Paragraph(f"SALARY SLIP FOR {month_name.upper()} {payroll_record.year}", header_badge_style))
    story.append(Spacer(1, 12))

    # Employee Meta Grid
    emp = payroll_record.employee
    meta_data = [
        [
            Paragraph("<b>Employee ID:</b>", label_style), Paragraph(str(emp.employee_id), val_style),
            Paragraph("<b>Payslip Number:</b>", label_style), Paragraph(str(payroll_record.payslip_number), val_style),
        ],
        [
            Paragraph("<b>Full Name:</b>", label_style), Paragraph(str(emp.full_name), val_style),
            Paragraph("<b>Pay Period:</b>", label_style), Paragraph(f"{month_name} {payroll_record.year}", val_style),
        ],
        [
            Paragraph("<b>Department:</b>", label_style), Paragraph(str(emp.department.name), val_style),
            Paragraph("<b>Status:</b>", label_style), Paragraph(str(payroll_record.get_status_display()), val_style),
        ],
        [
            Paragraph("<b>Designation:</b>", label_style), Paragraph(str(emp.designation), val_style),
            Paragraph("<b>Generated On:</b>", label_style), Paragraph(payroll_record.processed_at.strftime('%Y-%m-%d'), val_style),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[100, 170, 100, 170])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Earnings & Deductions Breakdown Table
    table_data = [
        [
            Paragraph("<b>EARNINGS</b>", label_style),
            Paragraph("<b>AMOUNT ($)</b>", label_style),
            Paragraph("<b>DEDUCTIONS</b>", label_style),
            Paragraph("<b>AMOUNT ($)</b>", label_style)
        ],
        [
            Paragraph("Basic Salary", val_style),
            Paragraph(f"{payroll_record.basic_salary:,.2f}", val_style),
            Paragraph("Provident Fund (PF)", val_style),
            Paragraph(f"{payroll_record.pf_deduction:,.2f}", val_style)
        ],
        [
            Paragraph("House Rent Allowance (HRA)", val_style),
            Paragraph(f"{payroll_record.hra:,.2f}", val_style),
            Paragraph("Professional / Statutory Tax", val_style),
            Paragraph(f"{payroll_record.tax_deduction:,.2f}", val_style)
        ],
        [
            Paragraph("Special & Other Allowances", val_style),
            Paragraph(f"{payroll_record.allowances_total:,.2f}", val_style),
            Paragraph("Unpaid Leave Adjustments", val_style),
            Paragraph(f"{payroll_record.unpaid_leave_deduction:,.2f}", val_style)
        ],
        [
            Paragraph("Performance Bonus / Incentives", val_style),
            Paragraph(f"{payroll_record.bonus:,.2f}", val_style),
            Paragraph("-", val_style),
            Paragraph("0.00", val_style)
        ],
        [
            Paragraph("<b>TOTAL GROSS EARNINGS</b>", label_style),
            Paragraph(f"<b>${payroll_record.gross_salary:,.2f}</b>", label_style),
            Paragraph("<b>TOTAL DEDUCTIONS</b>", label_style),
            Paragraph(f"<b>${payroll_record.total_deductions:,.2f}</b>", label_style)
        ],
    ]

    calc_table = Table(table_data, colWidths=[170, 100, 170, 100])
    calc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94a3b8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (1,1), (1,-1), 'RIGHT'),
        ('ALIGN', (3,1), (3,-1), 'RIGHT'),
    ]))
    story.append(calc_table)
    story.append(Spacer(1, 15))

    # Net Salary Highlight Banner
    net_data = [
        [
            Paragraph("<b>NET TAKE-HOME SALARY:</b>", ParagraphStyle('NetLabel', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#0f172a'))),
            Paragraph(f"<b>${payroll_record.net_salary:,.2f}</b>", ParagraphStyle('NetVal', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#166534'), alignment=2))
        ]
    ]
    net_table = Table(net_data, colWidths=[270, 270])
    net_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#dcfce7')),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#86efac')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 15),
        ('RIGHTPADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(net_table)
    story.append(Spacer(1, 25))

    # Footer Notice & Signatures
    footer_data = [
        [
            Paragraph("<i>This is a computer-generated payslip and requires no physical seal.<br/>For any payroll queries, please reach out to HR Operations.</i>", val_style),
            Paragraph("<b>Authorized Signatory</b><br/><br/>____________________________<br/>Director of Human Resources", ParagraphStyle('Sign', fontName='Helvetica', fontSize=8, alignment=2))
        ]
    ]
    footer_table = Table(footer_data, colWidths=[340, 200])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
    ]))
    story.append(footer_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

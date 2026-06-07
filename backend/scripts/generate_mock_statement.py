import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf(filename="mock_statement.pdf"):
    # Target path in workspace
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=20
    )
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#1E293B')
    )
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#334155')
    )
    amount_style_debit = ParagraphStyle(
        'AmountStyleDebit',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=colors.HexColor('#DC2626'),
        alignment=2 # Right aligned
    )
    amount_style_credit = ParagraphStyle(
        'AmountStyleCredit',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=colors.HexColor('#16A34A'),
        alignment=2 # Right aligned
    )

    # Title & Metadata
    story.append(Paragraph("APEX GLOBAL BANKING", title_style))
    story.append(Paragraph("ACCOUNT STATEMENT | CUSTOMER CONFIDENTIAL | DEMO PURPOSES ONLY", subtitle_style))
    
    # Account Info block
    info_data = [
        [Paragraph("<b>Customer Name:</b> Alice Sen", cell_style), Paragraph("<b>Statement Period:</b> 01-Jun-2026 to 15-Jun-2026", cell_style)],
        [Paragraph("<b>Account Number:</b> 987654321098", cell_style), Paragraph("<b>Email:</b> alice.freelancer@example.com", cell_style)],
        [Paragraph("<b>PAN Number:</b> ABCDE1234F", cell_style), Paragraph("<b>Phone:</b> +91 98765 43210", cell_style)],
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Transaction headers
    tx_data = [
        [
            Paragraph("<b>Date</b>", header_style),
            Paragraph("<b>Description</b>", header_style),
            Paragraph("<b>Type</b>", header_style),
            Paragraph("<b>Amount (INR)</b>", header_style)
        ]
    ]
    
    # Mock Transactions representing a Freelancer account
    transactions = [
        ("02-06-2026", "MONTHLY SALARY INFLOW", "CREDIT", "85,000.00"),
        ("03-06-2026", "UBER RIDE TRAVEL MUMBAI", "DEBIT", "350.00"),
        ("04-06-2026", "ZOMATO FRUIT SALAD ORDER", "DEBIT", "620.00"),
        ("05-06-2026", "AWS CLOUD ENGINE HOSTING", "DEBIT", "2,400.00"),
        ("06-06-2026", "LIC LIFE INSURANCE ANNUNITY", "DEBIT", "15,000.00"),
        ("08-06-2026", "GITHUB COPILOT SUBSCRIPTION", "DEBIT", "1,200.00"),
        ("10-06-2026", "HDFC HEALTH SURAKSHA POLICY", "DEBIT", "8,500.00"),
        ("11-06-2026", "JIO BROADBAND SERVICES", "DEBIT", "1,200.00"),
        ("12-06-2026", "APEX CO-WORKING SPACE RENT", "DEBIT", "12,000.00"),
        ("14-06-2026", "MUTUAL FUND SIP DEPOSIT", "DEBIT", "5,000.00"),
    ]
    
    for dt, desc, txtype, amt in transactions:
        amt_p = Paragraph(f"₹{amt}", amount_style_credit if txtype == "CREDIT" else amount_style_debit)
        tx_data.append([
            Paragraph(dt, cell_style),
            Paragraph(desc, cell_style),
            Paragraph(txtype, cell_style),
            amt_p
        ])
        
    tx_table = Table(tx_data, colWidths=[80, 260, 60, 100])
    tx_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
    ]))
    
    story.append(tx_table)
    
    # Build document
    doc.build(story)
    print(f"Mock statement generated successfully: {filename}")

if __name__ == "__main__":
    generate_pdf()

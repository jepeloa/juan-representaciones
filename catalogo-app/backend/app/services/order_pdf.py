"""PDF rendering for orders.

Uses ReportLab platypus to lay out an A4 doc with:
    * header: logo + company name + date + order id
    * customer info: user
    * items table per currency (ARS / USD)
    * payment condition + totals
    * disclaimer + terms (from settings)
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from app.models import Order, User

# Paleta pastel (deepened) — coherente con la app
COL_BRAND = colors.HexColor('#557390')
COL_BRAND_DARK = colors.HexColor('#384c60')
COL_SAGE = colors.HexColor('#6e8478')
COL_BEIGE = colors.HexColor('#967c4e')
COL_CREAM = colors.HexColor('#f7f3e8')
COL_CREAM_DARK = colors.HexColor('#efe8d3')
COL_TEXT = colors.HexColor('#384c60')
COL_MUTED = colors.HexColor('#6f8ca6')

LOGO_PATH = Path('/app/static/logo.png')


def _fmt_money(v: Decimal | None, currency: str | None = None) -> str:
    if v is None:
        return '—'
    sign = 'US$ ' if currency == 'USD' else '$ '
    # AR-style: thousands '.', decimal ','
    n = Decimal(v)
    int_part, _, dec_part = f'{n:,.2f}'.partition('.')
    int_part = int_part.replace(',', '.')
    return f'{sign}{int_part},{dec_part}'


def build_order_pdf(buf: BytesIO, *, order: Order, user: User, settings: dict[str, str | None]) -> None:
    company = settings.get('company_name') or 'Catálogo Juan'
    contact = settings.get('company_contact') or ''
    disclaimer = settings.get('catalog_disclaimer') or (
        'Los precios del catálogo son estimativos y pueden variar. '
        'Esta orden es un presupuesto sujeto a confirmación.'
    )
    terms = settings.get('catalog_terms') or ''

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f'Orden {order.id}',
        author=company,
    )

    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id='main')

    def on_page(canv, _doc):
        canv.saveState()
        canv.setFont('Helvetica', 8)
        canv.setFillColor(COL_MUTED)
        canv.drawRightString(A4[0] - 18 * mm, 12 * mm,
                             f'Página {_doc.page}')
        canv.drawString(18 * mm, 12 * mm, company)
        canv.restoreState()

    doc.addPageTemplates([PageTemplate(id='base', frames=[frame], onPage=on_page)])

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontName='Helvetica-Bold',
                                 fontSize=22, leading=26, textColor=COL_BRAND_DARK, alignment=TA_LEFT)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Helvetica-Bold',
                        fontSize=11, leading=15, textColor=COL_BRAND_DARK, spaceAfter=4)
    body = ParagraphStyle('Body', parent=styles['BodyText'], fontName='Helvetica',
                          fontSize=9.5, leading=13, textColor=COL_TEXT)
    muted = ParagraphStyle('Muted', parent=body, textColor=COL_MUTED, fontSize=8.5, leading=11)
    label = ParagraphStyle('Label', parent=body, textColor=COL_MUTED, fontSize=8,
                           fontName='Helvetica-Bold')

    story = []

    # ===== Header =====
    header_cells = []
    logo_cell = ''
    if LOGO_PATH.exists():
        try:
            logo_cell = Image(str(LOGO_PATH), width=24 * mm, height=24 * mm)
        except Exception:
            logo_cell = ''
    right_block = [
        Paragraph(f"<b>Orden #{order.id}</b>", h2),
        Paragraph(order.created_at.strftime('%d/%m/%Y %H:%M'), muted),
    ]
    left_block = [
        Paragraph(company, title_style),
        Paragraph(contact, muted) if contact else Paragraph('', muted),
    ]
    header_table = Table(
        [[logo_cell, left_block, right_block]],
        colWidths=[28 * mm, None, 45 * mm],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # Divider
    divider = Table([['']], colWidths=[doc.width], rowHeights=[0.6])
    divider.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), COL_CREAM_DARK)]))
    story.append(divider)
    story.append(Spacer(1, 5 * mm))

    # ===== Cliente + condición =====
    client_name = user.full_name or user.username
    info_rows = [
        [Paragraph('CLIENTE', label), Paragraph(client_name, body)],
        [Paragraph('USUARIO', label), Paragraph(user.username, body)],
    ]
    if order.payment_name:
        info_rows.append([
            Paragraph('CONDICIÓN', label),
            Paragraph(
                f"{order.payment_name} "
                f"<font color='#6e8478'>(× {order.payment_multiplier})</font>",
                body,
            ),
        ])
    if order.customer_notes:
        info_rows.append([Paragraph('NOTAS', label), Paragraph(order.customer_notes, body)])
    info_table = Table(info_rows, colWidths=[26 * mm, None])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6 * mm))

    # ===== Items table — split by currency; cada producto lista sus formas de pago =====
    ars_items = [it for it in order.items if it.currency == 'ARS']
    usd_items = [it for it in order.items if it.currency == 'USD']

    def items_block(items, currency):
        header = ['Producto', 'Cód.', 'Cant.', 'P. lista', 'P. final', 'Subtotal']
        rows = [header]
        for it in items:
            prod = it.product_name
            if it.supplier_name:
                prod += f"<br/><font color='#6e8478' size='7'>{it.supplier_name}</font>"
            if it.payment_term:
                prod += f"<br/><font color='#557390' size='7'>Condiciones de pago: {it.payment_term}</font>"
            rows.append([
                Paragraph(prod, body),
                Paragraph(it.product_code or '', muted),
                str(it.quantity),
                _fmt_money(it.unit_price_list, currency),
                _fmt_money(it.unit_price_final, currency),
                _fmt_money(it.line_total, currency),
            ])
        tbl = Table(rows, colWidths=[60 * mm, 22 * mm, 13 * mm, 26 * mm, 26 * mm, 26 * mm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COL_CREAM_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), COL_BRAND_DARK),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COL_CREAM]),
            ('LINEBELOW', (0, 0), (-1, 0), 0.4, COL_BEIGE),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        return tbl

    if ars_items:
        story.append(Paragraph(f"Productos en pesos (ARS) · {len(ars_items)} ítem(s)", h2))
        story.append(items_block(ars_items, 'ARS'))
        story.append(Spacer(1, 4 * mm))
    if usd_items:
        story.append(Paragraph(f"Productos en dólares (USD) · {len(usd_items)} ítem(s)", h2))
        story.append(items_block(usd_items, 'USD'))
        story.append(Spacer(1, 4 * mm))

    # ===== Totals =====
    total_rows = []
    if ars_items:
        total_rows.append([Paragraph('Subtotal lista (ARS)', muted),
                           _fmt_money(order.subtotal_ars, 'ARS')])
        total_rows.append([Paragraph(
            f"<b>Total ARS</b> con {order.payment_name or 'precio lista'}", body),
            _fmt_money(order.total_ars, 'ARS')])
    if usd_items:
        total_rows.append([Paragraph('Subtotal lista (USD)', muted),
                           _fmt_money(order.subtotal_usd, 'USD')])
        total_rows.append([Paragraph(
            f"<b>Total USD</b> con {order.payment_name or 'precio lista'}", body),
            _fmt_money(order.total_usd, 'USD')])
    if total_rows:
        tt = Table(total_rows, colWidths=[None, 38 * mm])
        styles_tt = [
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        # Style total rows (every 2nd row from 1) with stronger background
        for r in range(1, len(total_rows), 2):
            styles_tt.append(('BACKGROUND', (0, r), (-1, r), COL_BRAND))
            styles_tt.append(('TEXTCOLOR', (0, r), (-1, r), colors.white))
            styles_tt.append(('FONTNAME', (1, r), (1, r), 'Helvetica-Bold'))
        tt.setStyle(TableStyle(styles_tt))
        story.append(tt)
        story.append(Spacer(1, 6 * mm))

    # ===== Disclaimer / terms =====
    if disclaimer:
        story.append(Paragraph('Aclaración', h2))
        story.append(Paragraph(disclaimer.replace('\n', '<br/>'), body))
        story.append(Spacer(1, 4 * mm))
    if terms:
        story.append(Paragraph('Términos y condiciones', h2))
        story.append(Paragraph(terms.replace('\n', '<br/>'), muted))

    doc.build(story)

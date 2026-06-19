"""PDF rendering for orders.

Layout (A4):
    * header: logo JMG + order id / date
    * customer info (cliente / usuario / notas)
    * one SECTION PER BRAND (marca): each brand has its own products table,
      its own payment conditions and its own totals — como órdenes separadas.
    * disclaimer + terms (from settings)
"""
from __future__ import annotations
from collections import OrderedDict
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
from reportlab.lib.enums import TA_LEFT, TA_RIGHT

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

# Logo JMG (si no existe, cae al logo genérico)
_LOGO_JMG = Path('/app/static/logo_jmg.png')
_LOGO_FALLBACK = Path('/app/static/logo.png')
LOGO_PATH = _LOGO_JMG if _LOGO_JMG.exists() else _LOGO_FALLBACK


def _fmt_money(v: Decimal | None, currency: str | None = None) -> str:
    if v is None:
        return '—'
    sign = 'US$ ' if currency == 'USD' else '$ '
    n = Decimal(v)
    int_part, _, dec_part = f'{n:,.2f}'.partition('.')
    int_part = int_part.replace(',', '.')
    return f'{sign}{int_part},{dec_part}'


def build_order_pdf(
    buf: BytesIO, *, order: Order, user: User, settings: dict[str, str | None],
    brand_conditions: dict[str, list[str]] | None = None,
) -> None:
    brand_conditions = brand_conditions or {}
    company = settings.get('company_name') or 'JMG Representaciones'
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
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='main')

    def on_page(canv, _doc):
        canv.saveState()
        canv.setFont('Helvetica', 8)
        canv.setFillColor(COL_MUTED)
        canv.drawRightString(A4[0] - 18 * mm, 12 * mm, f'Página {_doc.page}')
        canv.drawString(18 * mm, 12 * mm, company)
        canv.restoreState()

    doc.addPageTemplates([PageTemplate(id='base', frames=[frame], onPage=on_page)])

    styles = getSampleStyleSheet()
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Helvetica-Bold',
                        fontSize=11, leading=15, textColor=COL_BRAND_DARK, spaceAfter=4)
    brand_h = ParagraphStyle('BrandH', parent=styles['Heading2'], fontName='Helvetica-Bold',
                             fontSize=13, leading=17, textColor=COL_BRAND, spaceAfter=2)
    body = ParagraphStyle('Body', parent=styles['BodyText'], fontName='Helvetica',
                          fontSize=9.5, leading=13, textColor=COL_TEXT)
    muted = ParagraphStyle('Muted', parent=body, textColor=COL_MUTED, fontSize=8.5, leading=11)
    cond_style = ParagraphStyle('Cond', parent=body, textColor=COL_BRAND, fontSize=8.5, leading=12)
    label = ParagraphStyle('Label', parent=body, textColor=COL_MUTED, fontSize=8, fontName='Helvetica-Bold')

    story = []

    # ===== Header (logo JMG) =====
    logo_cell = ''
    if LOGO_PATH.exists():
        try:
            logo_cell = Image(str(LOGO_PATH), width=48 * mm, height=22 * mm, kind='proportional')
            logo_cell.hAlign = 'LEFT'
        except Exception:
            logo_cell = ''
    right_block = [
        Paragraph(f"<b>Orden #{order.id}</b>", h2),
        Paragraph(order.created_at.strftime('%d/%m/%Y %H:%M'), muted),
    ]
    header_table = Table([[logo_cell, right_block]], colWidths=[None, 45 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    divider = Table([['']], colWidths=[doc.width], rowHeights=[0.6])
    divider.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), COL_CREAM_DARK)]))
    story.append(divider)
    story.append(Spacer(1, 5 * mm))

    # ===== Cliente =====
    client_name = user.full_name or user.username
    info_rows = [
        [Paragraph('CLIENTE', label), Paragraph(client_name, body)],
        [Paragraph('USUARIO', label), Paragraph(user.username, body)],
    ]
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
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph('Los precios indicados no incluyen IVA.', muted))
    story.append(Spacer(1, 5 * mm))

    # ===== Agrupado por MARCA =====
    brands: "OrderedDict[str, list]" = OrderedDict()
    for it in order.items:
        brands.setdefault(it.supplier_name or 'Sin marca', []).append(it)

    def items_table(items):
        header = ['Producto', 'Cód.', 'Cant.', 'Precio', 'Subtotal']
        rows = [header]
        for it in items:
            rows.append([
                Paragraph(it.product_name, body),
                Paragraph(it.product_code or '', muted),
                str(it.quantity),
                _fmt_money(it.unit_price_final, it.currency),
                _fmt_money(it.line_total, it.currency),
            ])
        tbl = Table(rows, colWidths=[78 * mm, 24 * mm, 14 * mm, 28 * mm, 30 * mm])
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

    for brand in sorted(brands):
        items = brands[brand]
        story.append(Paragraph(brand, brand_h))

        conds = brand_conditions.get(brand) or []
        if conds:
            story.append(Paragraph('Condiciones de pago:', label))
            for c in conds:
                story.append(Paragraph(c.replace('\n', '<br/>'), cond_style))
            story.append(Spacer(1, 2 * mm))

        story.append(items_table(items))

        # Totales de la marca por moneda
        tot = {'ARS': Decimal('0'), 'USD': Decimal('0')}
        for it in items:
            cur = it.currency or 'ARS'
            tot[cur] = tot.get(cur, Decimal('0')) + Decimal(it.line_total or 0)
        total_rows = []
        for cur in ('ARS', 'USD'):
            if tot[cur] > 0:
                total_rows.append([
                    Paragraph(f"<b>Total {brand} ({cur})</b> <font size='7'>+ IVA</font>", body),
                    _fmt_money(tot[cur], cur),
                ])
        if total_rows:
            tt = Table(total_rows, colWidths=[None, 40 * mm])
            st = [
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9.5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 0), (-1, -1), COL_BRAND),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ]
            tt.setStyle(TableStyle(st))
            story.append(Spacer(1, 1.5 * mm))
            story.append(tt)

        story.append(Spacer(1, 7 * mm))

    # ===== Disclaimer / terms =====
    if disclaimer:
        story.append(Paragraph('Aclaración', h2))
        story.append(Paragraph(disclaimer.replace('\n', '<br/>'), body))
        story.append(Spacer(1, 4 * mm))
    if terms:
        story.append(Paragraph('Términos y condiciones', h2))
        story.append(Paragraph(terms.replace('\n', '<br/>'), muted))

    doc.build(story)

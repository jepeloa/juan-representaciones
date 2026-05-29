"""SMTP email service for sending order PDFs.

SMTP credentials live in env vars (config.py). The recipient address is the
'order_notification_email' setting (configurable from admin).

If SMTP_HOST is empty, emails are 'disabled' — we log the action and mark the
order's email_status='disabled' so admin can see the email wasn't actually sent.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import SessionLocal
from app.models import Order, Setting, User
from app.services.order_pdf import build_order_pdf

log = logging.getLogger('mailer')


def _fmt_money_short(v, currency: str | None) -> str:
    if v is None:
        return '—'
    n = float(v)
    int_part, _, dec_part = f'{n:,.2f}'.partition('.')
    int_part = int_part.replace(',', '.')
    pre = 'US$ ' if currency == 'USD' else '$ '
    return f'{pre}{int_part},{dec_part}'


def _render_html_body(order: Order, user: User, company: str) -> str:
    rows = []
    for it in order.items:
        rows.append(
            f"<tr>"
            f"<td style='padding:8px;border-bottom:1px solid #efe8d3;color:#384c60'>{it.product_name}"
            f"{f'<br><small style=color:#6e8478>{it.supplier_name}</small>' if it.supplier_name else ''}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #efe8d3;color:#6f8ca6;font-family:monospace;font-size:11px'>{it.product_code or ''}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #efe8d3;text-align:right'>{it.quantity}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #efe8d3;text-align:right'>{_fmt_money_short(it.unit_price_final, it.currency)}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #efe8d3;text-align:right;font-weight:600'>{_fmt_money_short(it.line_total, it.currency)}</td>"
            f"</tr>"
        )
    totals = []
    if order.total_ars and float(order.total_ars) > 0:
        totals.append(f"<tr><td colspan=4 style='padding:8px;text-align:right;font-weight:600;color:#384c60'>Total ARS</td>"
                      f"<td style='padding:8px;text-align:right;font-weight:700;color:#6e8478'>{_fmt_money_short(order.total_ars, 'ARS')}</td></tr>")
    if order.total_usd and float(order.total_usd) > 0:
        totals.append(f"<tr><td colspan=4 style='padding:8px;text-align:right;font-weight:600;color:#384c60'>Total USD</td>"
                      f"<td style='padding:8px;text-align:right;font-weight:700;color:#557390'>{_fmt_money_short(order.total_usd, 'USD')}</td></tr>")
    client_name = user.full_name or user.username
    return f"""<!DOCTYPE html>
<html><body style="font-family: 'Inter', sans-serif; background:#f7f3e8; padding: 24px; color:#384c60;">
<div style="max-width:720px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;border:1px solid #efe8d3">
    <div style="background:#557390;padding:20px 24px;color:white">
        <h1 style="margin:0;font-size:20px;font-weight:700">{company}</h1>
        <p style="margin:4px 0 0;opacity:.9;font-size:13px">Nueva orden #{order.id}</p>
    </div>
    <div style="padding:20px 24px">
        <p>Recibiste una nueva orden generada desde el catálogo.</p>
        <table style="margin:14px 0;border-collapse:collapse">
            <tr><td style="color:#6f8ca6;font-size:12px;padding-right:12px">CLIENTE</td><td><b>{client_name}</b> ({user.username})</td></tr>
            <tr><td style="color:#6f8ca6;font-size:12px;padding-right:12px">FECHA</td><td>{order.created_at.strftime('%d/%m/%Y %H:%M')}</td></tr>
            {'<tr><td style="color:#6f8ca6;font-size:12px;padding-right:12px">CONDICIÓN</td><td>' + (order.payment_name or '') + f' (× {order.payment_multiplier})</td></tr>' if order.payment_name else ''}
            {'<tr><td style="color:#6f8ca6;font-size:12px;padding-right:12px;vertical-align:top">NOTAS</td><td>' + (order.customer_notes or '').replace(chr(10), '<br>') + '</td></tr>' if order.customer_notes else ''}
        </table>
        <table style="width:100%;border-collapse:collapse;margin-top:16px;font-size:13px">
            <thead><tr style="background:#efe8d3;color:#384c60">
                <th style="padding:8px;text-align:left">Producto</th>
                <th style="padding:8px;text-align:left">Cód.</th>
                <th style="padding:8px;text-align:right">Cant.</th>
                <th style="padding:8px;text-align:right">P. final</th>
                <th style="padding:8px;text-align:right">Subtotal</th>
            </tr></thead>
            <tbody>{''.join(rows)}</tbody>
            <tfoot>{''.join(totals)}</tfoot>
        </table>
        <p style="color:#6f8ca6;font-size:12px;margin-top:16px">
            El detalle completo está adjunto en PDF. Esta orden se generó automáticamente desde el catálogo;
            los precios son estimativos y deben confirmarse antes de procesar.
        </p>
    </div>
</div>
</body></html>"""


def _build_pdf_bytes(order: Order, user: User, db_settings: dict[str, str | None]) -> bytes:
    buf = BytesIO()
    build_order_pdf(buf, order=order, user=user, settings=db_settings)
    return buf.getvalue()


def send_order_email(order_id: int) -> None:
    """Send the order PDF to the configured recipient.

    Designed to be called from a FastAPI BackgroundTask, so it manages its own
    DB session. Updates the order's email_status / email_sent_at fields.
    """
    db: Session = SessionLocal()
    try:
        order = db.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        ).scalar_one_or_none()
        if not order:
            log.warning('send_order_email: order %s not found', order_id)
            return
        user = db.get(User, order.user_id) if order.user_id else None
        if not user:
            order.email_status = 'failed'
            order.email_error = 'usuario asociado no encontrado'
            db.commit()
            return

        settings_rows = db.execute(select(Setting)).scalars().all()
        db_settings = {s.key: s.value for s in settings_rows}
        recipient = (db_settings.get('order_notification_email') or '').strip()
        company = db_settings.get('company_name') or 'Catálogo'

        if not recipient:
            order.email_status = 'disabled'
            order.email_error = 'No hay email destinatario configurado en /admin/condiciones'
            db.commit()
            log.info('Order %s: email skipped — no recipient configured', order.id)
            return

        if not settings.SMTP_HOST:
            order.email_status = 'disabled'
            order.email_error = 'SMTP no configurado en el servidor (env SMTP_HOST vacío)'
            order.email_to = recipient
            db.commit()
            log.info('Order %s: would send to %s but SMTP_HOST is empty', order.id, recipient)
            return

        # Build PDF
        pdf_bytes = _build_pdf_bytes(order, user, db_settings)
        html_body = _render_html_body(order, user, company)

        msg = EmailMessage()
        msg['Subject'] = f"Nueva orden #{order.id} — {user.full_name or user.username}"
        msg['From'] = settings.SMTP_FROM or settings.SMTP_USER
        msg['To'] = recipient
        msg.set_content(
            f"Nueva orden #{order.id} de {user.full_name or user.username}.\n"
            f"Total ARS: {_fmt_money_short(order.total_ars, 'ARS') if order.total_ars else '-'}\n"
            f"Total USD: {_fmt_money_short(order.total_usd, 'USD') if order.total_usd else '-'}\n"
            f"Ver detalle en el PDF adjunto.\n"
        )
        msg.add_alternative(html_body, subtype='html')
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=f'orden-{order.id}.pdf')

        try:
            if settings.SMTP_PORT == 465:
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=ctx, timeout=20) as s:
                    if settings.SMTP_USER:
                        s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
                    s.ehlo()
                    if settings.SMTP_USE_TLS:
                        s.starttls(context=ssl.create_default_context())
                        s.ehlo()
                    if settings.SMTP_USER:
                        s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    s.send_message(msg)
            order.email_status = 'sent'
            order.email_to = recipient
            order.email_sent_at = datetime.utcnow()
            order.email_error = None
            db.commit()
            log.info('Order %s emailed to %s', order.id, recipient)
        except Exception as e:
            order.email_status = 'failed'
            order.email_to = recipient
            order.email_error = str(e)[:500]
            db.commit()
            log.exception('Order %s: SMTP send failed', order.id)
    finally:
        db.close()

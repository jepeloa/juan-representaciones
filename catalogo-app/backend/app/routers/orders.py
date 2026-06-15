from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import (
    PaymentCondition, Setting, Order, OrderItem, Product, User, Supplier,
)
from app.schemas import (
    PaymentConditionOut, OrderCreateIn, OrderOut, OrderItemOut, SettingsOut,
)

router = APIRouter(prefix='/api', tags=['orders'])


@router.get('/payment-conditions', response_model=list[PaymentConditionOut])
def list_active_conditions(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.execute(
        select(PaymentCondition)
        .where(PaymentCondition.is_active.is_(True))
        .order_by(PaymentCondition.sort_order, PaymentCondition.name)
    ).scalars().all()
    return list(rows)


@router.get('/settings/public', response_model=SettingsOut)
def public_settings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    # Public exposes only catalog/company info — never the notification email
    keys = ['catalog_disclaimer', 'catalog_terms', 'company_name', 'company_contact']
    rows = db.execute(select(Setting).where(Setting.key.in_(keys))).scalars().all()
    by_key = {r.key: r.value for r in rows}
    return SettingsOut(**{k: by_key.get(k) for k in keys})


def _quantize(d: Decimal) -> Decimal:
    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _build_order_items(db: Session, items_in: list, condition: PaymentCondition | None) -> tuple[list[OrderItem], Decimal, Decimal, Decimal, Decimal]:
    multiplier = condition.multiplier if condition else Decimal('1.0000')
    out_items: list[OrderItem] = []
    sub_ars = Decimal('0')
    sub_usd = Decimal('0')
    tot_ars = Decimal('0')
    tot_usd = Decimal('0')
    for it in items_in:
        product = db.execute(
            select(Product)
            .options(selectinload(Product.supplier).selectinload(Supplier.payment_conditions))
            .where(Product.id == it.product_id)
        ).scalar_one_or_none()
        if not product:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f'Producto id={it.product_id} no encontrado')
        if product.price is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f'Producto "{product.name}" no tiene precio cargado (consultar al proveedor)',
            )
        qty = max(1, int(it.quantity))
        # Si el producto está en oferta, el precio de oferta reemplaza al de lista
        # como base; la condición de pago (multiplicador) se aplica sobre esa base.
        if product.is_offer and product.offer_price is not None:
            unit_list = Decimal(product.offer_price)
        else:
            unit_list = Decimal(product.price)
        unit_final = _quantize(unit_list * multiplier)
        line_total = _quantize(unit_final * qty)
        sub_line = _quantize(unit_list * qty)
        currency = product.currency or 'ARS'
        if currency == 'USD':
            sub_usd += sub_line
            tot_usd += line_total
        else:
            sub_ars += sub_line
            tot_ars += line_total
        out_items.append(OrderItem(
            product_id=product.id,
            quantity=qty,
            unit_price_list=unit_list,
            unit_price_final=unit_final,
            currency=currency,
            line_total=line_total,
            product_name=product.name,
            product_code=product.code,
            supplier_name=product.supplier.name if product.supplier else None,
            payment_term=(', '.join(
                c.name for c in product.supplier.payment_conditions if c.is_active
            ) if product.supplier else '') or None,
        ))
    return out_items, _quantize(sub_ars), _quantize(tot_ars), _quantize(sub_usd), _quantize(tot_usd)


@router.post('/orders', response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    body: OrderCreateIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'La orden no tiene ítems')
    condition = None
    if body.payment_condition_id:
        condition = db.get(PaymentCondition, body.payment_condition_id)
        if not condition or not condition.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Condición de pago no válida')
    items, sub_ars, tot_ars, sub_usd, tot_usd = _build_order_items(db, body.items, condition)
    order = Order(
        user_id=user.id,
        payment_condition_id=condition.id if condition else None,
        payment_name=condition.name if condition else None,
        payment_multiplier=condition.multiplier if condition else Decimal('1.0000'),
        subtotal_ars=sub_ars,
        total_ars=tot_ars,
        subtotal_usd=sub_usd,
        total_usd=tot_usd,
        customer_notes=body.customer_notes,
        status='submitted',
        email_status='pending',
    )
    order.items = items
    db.add(order)
    db.commit()
    db.refresh(order)

    # Fire-and-forget email send
    from app.services.mailer import send_order_email
    background.add_task(send_order_email, order.id)

    return order


@router.post('/orders/{order_id}/resend', response_model=OrderOut)
def resend_order_email(
    order_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Orden no encontrada')
    if order.user_id != user.id and not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'No tenés acceso a esta orden')
    order.email_status = 'pending'
    order.email_error = None
    db.commit()
    from app.services.mailer import send_order_email
    background.add_task(send_order_email, order.id)
    db.refresh(order)
    return order


@router.get('/orders', response_model=list[OrderOut])
def my_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(50)
    ).scalars().all()
    return list(rows)


@router.get('/orders/{order_id}/pdf')
def order_pdf(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Orden no encontrada')
    # Owner or admin can download
    if order.user_id != user.id and not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'No tenés acceso a esta orden')

    settings_rows = db.execute(select(Setting)).scalars().all()
    settings = {s.key: s.value for s in settings_rows}

    from app.services.order_pdf import build_order_pdf
    buf = BytesIO()
    build_order_pdf(buf, order=order, user=user, settings=settings)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type='application/pdf',
        headers={'Content-Disposition': f'inline; filename="orden-{order.id}.pdf"'},
    )

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import require_admin
from app.database import get_db
from app.models import User, ClientProfile, ActivityEvent, Order
from app.schemas import (
    ClientListItemOut, ClientDetailOut, ClientStatsOut, ClientProfileIn,
    ClientProfileOut, ActivityCount, TopProduct,
)
from app.schemas.clients import ActivityEventOut
from app.schemas.orders import OrderOut

router = APIRouter(prefix='/api/admin/clients', tags=['admin-clients'])


@router.get('', response_model=list[ClientListItemOut])
def list_clients(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.execute(
        select(User).where(User.is_admin.is_(False)).order_by(User.username)
    ).scalars().all()

    # Agregados de actividad por usuario
    ev_rows = db.execute(
        select(
            ActivityEvent.user_id,
            func.count(ActivityEvent.id),
            func.sum(case((ActivityEvent.event_type == 'login', 1), else_=0)),
            func.max(ActivityEvent.created_at),
        ).group_by(ActivityEvent.user_id)
    ).all()
    ev_by_user = {r[0]: (r[1] or 0, int(r[2] or 0), r[3]) for r in ev_rows}

    # Agregados de órdenes por usuario
    ord_rows = db.execute(
        select(
            Order.user_id,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_ars), 0),
            func.coalesce(func.sum(Order.total_usd), 0),
            func.max(Order.created_at),
        ).group_by(Order.user_id)
    ).all()
    ord_by_user = {r[0]: (r[1] or 0, r[2] or Decimal('0'), r[3] or Decimal('0'), r[4]) for r in ord_rows}

    # Perfiles (para company_name)
    prof_rows = db.execute(select(ClientProfile)).scalars().all()
    prof_by_user = {p.user_id: p for p in prof_rows}

    out: list[ClientListItemOut] = []
    for u in users:
        events_count, visits, ev_last = ev_by_user.get(u.id, (0, 0, None))
        orders_count, tot_ars, tot_usd, ord_last = ord_by_user.get(u.id, (0, Decimal('0'), Decimal('0'), None))
        last_active = max([d for d in (ev_last, ord_last) if d], default=None)
        prof = prof_by_user.get(u.id)
        out.append(ClientListItemOut(
            id=u.id, username=u.username, full_name=u.full_name,
            is_active=u.is_active, created_at=u.created_at,
            company_name=prof.company_name if prof else None,
            visits=visits, events_count=events_count, orders_count=orders_count,
            total_ars=tot_ars, total_usd=tot_usd, last_active=last_active,
        ))
    # Más activos primero
    out.sort(key=lambda c: (c.last_active is not None, c.last_active or c.created_at), reverse=True)
    return out


def _stats_for(db: Session, user_id: int) -> ClientStatsOut:
    by_type = db.execute(
        select(ActivityEvent.event_type, func.count(ActivityEvent.id))
        .where(ActivityEvent.user_id == user_id)
        .group_by(ActivityEvent.event_type)
    ).all()
    by_type_list = [ActivityCount(event_type=t, count=c) for t, c in by_type]
    counts = {t: c for t, c in by_type}

    first_last = db.execute(
        select(func.min(ActivityEvent.created_at), func.max(ActivityEvent.created_at))
        .where(ActivityEvent.user_id == user_id)
    ).one()

    ord_agg = db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_ars), 0),
            func.coalesce(func.sum(Order.total_usd), 0),
            func.max(Order.created_at),
        ).where(Order.user_id == user_id)
    ).one()

    top = db.execute(
        select(ActivityEvent.ref_id, func.max(ActivityEvent.label), func.count(ActivityEvent.id))
        .where(ActivityEvent.user_id == user_id, ActivityEvent.event_type == 'product_view')
        .group_by(ActivityEvent.ref_id)
        .order_by(func.count(ActivityEvent.id).desc())
        .limit(10)
    ).all()
    top_products = [TopProduct(ref_id=r[0], label=r[1], count=r[2]) for r in top]

    last_active = max([d for d in (first_last[1], ord_agg[3]) if d], default=None)

    return ClientStatsOut(
        visits=int(counts.get('login', 0)),
        events_count=sum(counts.values()),
        orders_count=ord_agg[0] or 0,
        total_ars=ord_agg[1] or Decimal('0'),
        total_usd=ord_agg[2] or Decimal('0'),
        first_active=first_last[0],
        last_active=last_active,
        by_type=by_type_list,
        top_products=top_products,
    )


@router.get('/{user_id}', response_model=ClientDetailOut)
def client_detail(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Usuario no encontrado')

    profile = db.execute(
        select(ClientProfile).where(ClientProfile.user_id == user_id)
    ).scalar_one_or_none()

    recent = db.execute(
        select(ActivityEvent)
        .where(ActivityEvent.user_id == user_id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(80)
    ).scalars().all()

    orders = db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(100)
    ).scalars().all()

    return ClientDetailOut(
        id=user.id, username=user.username, full_name=user.full_name,
        is_active=user.is_active, is_admin=user.is_admin, created_at=user.created_at,
        profile=ClientProfileOut.model_validate(profile) if profile else None,
        stats=_stats_for(db, user_id),
        recent_activity=[ActivityEventOut.model_validate(e) for e in recent],
        orders=[OrderOut.model_validate(o) for o in orders],
    )


@router.put('/{user_id}/profile', response_model=ClientProfileOut)
def upsert_profile(
    user_id: int,
    body: ClientProfileIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Usuario no encontrado')
    profile = db.execute(
        select(ClientProfile).where(ClientProfile.user_id == user_id)
    ).scalar_one_or_none()
    if not profile:
        profile = ClientProfile(user_id=user_id)
        db.add(profile)
    for field, value in body.model_dump().items():
        setattr(profile, field, (value or None))
    db.commit()
    db.refresh(profile)
    return profile

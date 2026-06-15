from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.database import get_db
from app.models import PaymentCondition, Setting, User, Supplier
from app.schemas import (
    PaymentConditionIn, PaymentConditionOut,
    SettingsBulkIn, SettingsOut,
)

router = APIRouter(prefix='/api/admin', tags=['admin-conditions'])


def _cond_out(pc: PaymentCondition) -> PaymentConditionOut:
    return PaymentConditionOut(
        id=pc.id, name=pc.name, description=pc.description, multiplier=pc.multiplier,
        days=pc.days, is_active=pc.is_active, sort_order=pc.sort_order,
        supplier_ids=[s.id for s in pc.suppliers],
    )


def _resolve_suppliers(db: Session, ids: list[int]) -> list[Supplier]:
    if not ids:
        return []
    sups = db.execute(select(Supplier).where(Supplier.id.in_(ids))).scalars().all()
    return list(sups)


# ===== Payment conditions =====
@router.get('/payment-conditions', response_model=list[PaymentConditionOut])
def list_conditions(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.execute(
        select(PaymentCondition).order_by(PaymentCondition.sort_order, PaymentCondition.name)
    ).scalars().all()
    return [_cond_out(pc) for pc in rows]


@router.post('/payment-conditions', response_model=PaymentConditionOut, status_code=status.HTTP_201_CREATED)
def create_condition(body: PaymentConditionIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    data = body.model_dump()
    supplier_ids = data.pop('supplier_ids', [])
    pc = PaymentCondition(**data)
    pc.suppliers = _resolve_suppliers(db, supplier_ids)
    db.add(pc)
    db.commit()
    db.refresh(pc)
    return _cond_out(pc)


@router.patch('/payment-conditions/{cond_id}', response_model=PaymentConditionOut)
def update_condition(cond_id: int, body: PaymentConditionIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    pc = db.get(PaymentCondition, cond_id)
    if not pc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Condición no encontrada')
    data = body.model_dump()
    supplier_ids = data.pop('supplier_ids', [])
    for k, v in data.items():
        setattr(pc, k, v)
    pc.suppliers = _resolve_suppliers(db, supplier_ids)
    db.commit()
    db.refresh(pc)
    return _cond_out(pc)


@router.delete('/payment-conditions/{cond_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_condition(cond_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    pc = db.get(PaymentCondition, cond_id)
    if not pc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Condición no encontrada')
    db.delete(pc)
    db.commit()


# ===== Settings (catalog disclaimer / terms / company info) =====
SETTING_KEYS = ['catalog_disclaimer', 'catalog_terms', 'company_name', 'company_contact', 'order_notification_email']


@router.get('/settings', response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.execute(select(Setting).where(Setting.key.in_(SETTING_KEYS))).scalars().all()
    by_key = {r.key: r.value for r in rows}
    return SettingsOut(**{k: by_key.get(k) for k in SETTING_KEYS})


@router.put('/settings', response_model=SettingsOut)
def update_settings(body: SettingsBulkIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    for key, value in body.settings.items():
        if key not in SETTING_KEYS:
            continue
        existing = db.get(Setting, key)
        if existing:
            existing.value = value
        else:
            db.add(Setting(key=key, value=value))
    db.commit()
    rows = db.execute(select(Setting).where(Setting.key.in_(SETTING_KEYS))).scalars().all()
    by_key = {r.key: r.value for r in rows}
    return SettingsOut(**{k: by_key.get(k) for k in SETTING_KEYS})

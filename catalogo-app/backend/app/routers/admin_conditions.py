from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.database import get_db
from app.models import PaymentCondition, Setting, User
from app.schemas import (
    PaymentConditionIn, PaymentConditionOut,
    SettingsBulkIn, SettingsOut,
)

router = APIRouter(prefix='/api/admin', tags=['admin-conditions'])


# ===== Payment conditions =====
@router.get('/payment-conditions', response_model=list[PaymentConditionOut])
def list_conditions(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.execute(
        select(PaymentCondition).order_by(PaymentCondition.sort_order, PaymentCondition.name)
    ).scalars().all()
    return list(rows)


@router.post('/payment-conditions', response_model=PaymentConditionOut, status_code=status.HTTP_201_CREATED)
def create_condition(body: PaymentConditionIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    pc = PaymentCondition(**body.model_dump())
    db.add(pc)
    db.commit()
    db.refresh(pc)
    return pc


@router.patch('/payment-conditions/{cond_id}', response_model=PaymentConditionOut)
def update_condition(cond_id: int, body: PaymentConditionIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    pc = db.get(PaymentCondition, cond_id)
    if not pc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Condición no encontrada')
    for k, v in body.model_dump().items():
        setattr(pc, k, v)
    db.commit()
    db.refresh(pc)
    return pc


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

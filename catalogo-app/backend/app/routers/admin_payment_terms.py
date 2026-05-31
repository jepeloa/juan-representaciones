"""Admin CRUD para condiciones de pago en texto libre (PaymentTerm).

Distinto de admin_conditions (multiplicador del checkout). Estas se asocian
opcionalmente a un proveedor y luego a productos; aparecen en la orden.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import require_admin
from app.database import get_db
from app.models import PaymentTerm, Supplier, User
from app.schemas import PaymentTermIn, PaymentTermOut

router = APIRouter(prefix='/api/admin/payment-terms', tags=['admin-payment-terms'])


def _to_out(t: PaymentTerm) -> PaymentTermOut:
    return PaymentTermOut(
        id=t.id,
        text=t.text,
        supplier_id=t.supplier_id,
        supplier_name=t.supplier.name if t.supplier else None,
        is_active=t.is_active,
        sort_order=t.sort_order,
    )


@router.get('', response_model=list[PaymentTermOut])
def list_terms(
    supplier_id: int | None = Query(None, description='Filtra por proveedor (incluye las globales sin proveedor)'),
    only_active: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = (
        select(PaymentTerm)
        .options(selectinload(PaymentTerm.supplier))
        .order_by(PaymentTerm.sort_order, PaymentTerm.id)
    )
    if supplier_id is not None:
        stmt = stmt.where(or_(PaymentTerm.supplier_id == supplier_id, PaymentTerm.supplier_id.is_(None)))
    if only_active:
        stmt = stmt.where(PaymentTerm.is_active.is_(True))
    rows = db.execute(stmt).scalars().all()
    return [_to_out(t) for t in rows]


@router.post('', response_model=PaymentTermOut, status_code=status.HTTP_201_CREATED)
def create_term(body: PaymentTermIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if body.supplier_id is not None and not db.get(Supplier, body.supplier_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Proveedor no encontrado')
    t = PaymentTerm(
        text=body.text.strip(),
        supplier_id=body.supplier_id,
        is_active=body.is_active,
        sort_order=body.sort_order,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.patch('/{term_id}', response_model=PaymentTermOut)
def update_term(term_id: int, body: PaymentTermIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    t = db.get(PaymentTerm, term_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Condición no encontrada')
    if body.supplier_id is not None and not db.get(Supplier, body.supplier_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Proveedor no encontrado')
    t.text = body.text.strip()
    t.supplier_id = body.supplier_id
    t.is_active = body.is_active
    t.sort_order = body.sort_order
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.delete('/{term_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_term(term_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    t = db.get(PaymentTerm, term_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Condición no encontrada')
    db.delete(t)
    db.commit()

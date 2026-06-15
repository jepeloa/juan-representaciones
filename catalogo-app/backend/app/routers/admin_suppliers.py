"""Admin: foto/logo de cada marca (Supplier.image)."""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.database import get_db
from app.models import Supplier, Product, PaymentCondition, User
from app.schemas import SupplierOut, PaymentConditionBrief, SupplierConditionsIn
from app.routers.admin_products import _save_image_file

router = APIRouter(prefix='/api/admin/suppliers', tags=['admin-suppliers'])


def _out(db: Session, sup: Supplier) -> SupplierOut:
    cnt = db.execute(
        select(func.count(Product.id)).where(Product.supplier_id == sup.id)
    ).scalar_one()
    return SupplierOut(
        id=sup.id, name=sup.name, slug=sup.slug, image=sup.image, product_count=cnt,
        payment_conditions=[
            PaymentConditionBrief(id=c.id, name=c.name, description=c.description)
            for c in sup.payment_conditions
        ],
    )


@router.put('/{supplier_id}/conditions', response_model=SupplierOut)
def set_supplier_conditions(
    supplier_id: int,
    body: SupplierConditionsIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    sup = db.get(Supplier, supplier_id)
    if not sup:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Marca no encontrada')
    if body.condition_ids:
        conds = db.execute(
            select(PaymentCondition).where(PaymentCondition.id.in_(body.condition_ids))
        ).scalars().all()
    else:
        conds = []
    sup.payment_conditions = list(conds)
    db.commit()
    db.refresh(sup)
    return _out(db, sup)


@router.post('/{supplier_id}/image', response_model=SupplierOut)
def upload_supplier_image(
    supplier_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    sup = db.get(Supplier, supplier_id)
    if not sup:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Marca no encontrada')
    sup.image = _save_image_file(file, 'brands')
    db.commit()
    db.refresh(sup)
    return _out(db, sup)


@router.delete('/{supplier_id}/image', response_model=SupplierOut)
def clear_supplier_image(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    sup = db.get(Supplier, supplier_id)
    if not sup:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Marca no encontrada')
    sup.image = None
    db.commit()
    db.refresh(sup)
    return _out(db, sup)

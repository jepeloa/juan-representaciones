"""Admin: foto/logo de cada marca (Supplier.image)."""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.database import get_db
from app.models import Supplier, Product, PaymentCondition, User
from app.schemas import SupplierOut, PaymentConditionBrief, SupplierConditionsIn, SupplierUpdateIn, ActiveIn
from app.routers.admin_products import _save_image_file

router = APIRouter(prefix='/api/admin/suppliers', tags=['admin-suppliers'])


@router.patch('/{supplier_id}', response_model=SupplierOut)
def update_supplier(
    supplier_id: int,
    body: SupplierUpdateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    sup = db.get(Supplier, supplier_id)
    if not sup:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Marca no encontrada')
    name = body.name.strip()
    dup = db.execute(
        select(Supplier).where(Supplier.name == name, Supplier.id != supplier_id)
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, f'Ya existe una marca llamada "{name}"')
    sup.name = name
    db.commit()
    db.refresh(sup)
    return _out(db, sup)


@router.delete('/{supplier_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    sup = db.get(Supplier, supplier_id)
    if not sup:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Marca no encontrada')
    cnt = db.execute(
        select(func.count(Product.id)).where(Product.supplier_id == supplier_id)
    ).scalar_one()
    if cnt > 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f'La marca tiene {cnt} producto(s). Reasigná o eliminá esos productos antes de borrar la marca.',
        )
    db.delete(sup)
    db.commit()


def _out(db: Session, sup: Supplier) -> SupplierOut:
    cnt = db.execute(
        select(func.count(Product.id)).where(Product.supplier_id == sup.id)
    ).scalar_one()
    return SupplierOut(
        id=sup.id, name=sup.name, slug=sup.slug, image=sup.image, product_count=cnt, is_active=sup.is_active,
        payment_conditions=[
            PaymentConditionBrief(id=c.id, name=c.name, description=c.description)
            for c in sup.payment_conditions
        ],
    )


@router.patch('/{supplier_id}/active', response_model=SupplierOut)
def set_supplier_active(
    supplier_id: int,
    body: ActiveIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    sup = db.get(Supplier, supplier_id)
    if not sup:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Marca no encontrada')
    sup.is_active = body.active
    # Cascada: inhabilitar/habilitar la marca replica en todos sus productos.
    db.execute(
        update(Product).where(Product.supplier_id == supplier_id).values(is_active=body.active)
    )
    db.commit()
    db.refresh(sup)
    return _out(db, sup)


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

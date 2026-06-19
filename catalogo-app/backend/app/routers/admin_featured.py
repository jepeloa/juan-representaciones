"""Admin: orden de destacados por sección (catálogo / ofertas).

Cada producto puede tener un orden manual por sección (catalog_order / offer_order).
NULL = no destacado. Menor número = aparece primero.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import require_admin
from app.database import get_db
from app.models import Product, Supplier, User
from app.schemas import ProductOut, FeaturedOrderIn
from app.routers.products import _row_to_out

router = APIRouter(prefix='/api/admin/featured', tags=['admin-featured'])

_COLS = {'catalog': 'catalog_order', 'offer': 'offer_order'}
_LOAD = (
    selectinload(Product.supplier).selectinload(Supplier.payment_conditions),
    selectinload(Product.category),
    selectinload(Product.images),
)


def _col(section: str):
    if section not in _COLS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Sección inválida (catalog | offer)')
    return getattr(Product, _COLS[section])


@router.get('/{section}', response_model=list[ProductOut])
def list_featured(section: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    col = _col(section)
    rows = db.execute(
        select(Product).options(*_LOAD).where(col.is_not(None)).order_by(col.asc(), Product.id.asc())
    ).scalars().all()
    return [_row_to_out(p) for p in rows]


@router.put('/{section}', response_model=list[ProductOut])
def set_featured(
    section: str,
    body: FeaturedOrderIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    col = _col(section)
    # Reset toda la columna y volver a setear el orden de los elegidos
    db.execute(update(Product).values({col: None}))
    for i, pid in enumerate(body.product_ids):
        db.execute(update(Product).where(Product.id == pid).values({col: i}))
    db.commit()
    rows = db.execute(
        select(Product).options(*_LOAD).where(col.is_not(None)).order_by(col.asc(), Product.id.asc())
    ).scalars().all()
    return [_row_to_out(p) for p in rows]

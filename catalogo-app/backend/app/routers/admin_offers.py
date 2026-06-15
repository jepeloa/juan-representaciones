"""Admin: gestión de ofertas (precio de oferta fijo + on/off por producto).

Una oferta no es una entidad aparte: vive en el propio producto
(offer_price + is_offer). Estos endpoints listan, setean y limpian ofertas.
Para encontrar productos a poner en oferta, el admin usa el buscador normal
(`GET /api/products?q=...`).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import require_admin
from app.database import get_db
from app.models import Product, User
from app.schemas import ProductOut, OfferUpdateIn
from app.routers.products import _row_to_out

router = APIRouter(prefix='/api/admin/offers', tags=['admin-offers'])

_LOAD = (
    selectinload(Product.supplier),
    selectinload(Product.category),
    selectinload(Product.images),
    selectinload(Product.payment_conditions),
)


def _load_product(db: Session, product_id: int) -> Product:
    p = db.execute(
        select(Product).options(*_LOAD).where(Product.id == product_id)
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Producto no encontrado')
    return p


@router.get('', response_model=list[ProductOut])
def list_offers(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Todos los productos con oferta cargada (activa o no), para gestionarlas."""
    rows = db.execute(
        select(Product).options(*_LOAD)
        .where(or_(Product.is_offer.is_(True), Product.offer_price.is_not(None)))
        .order_by(Product.is_offer.desc(), Product.name)
    ).scalars().all()
    return [_row_to_out(p) for p in rows]


@router.put('/{product_id}', response_model=ProductOut)
def set_offer(
    product_id: int,
    body: OfferUpdateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    p = _load_product(db, product_id)
    if body.is_offer and body.offer_price is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Para activar la oferta hay que cargar un precio de oferta',
        )
    if body.offer_price is not None and p.price is not None and body.offer_price >= p.price:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'El precio de oferta debe ser menor al precio de lista',
        )
    p.offer_price = body.offer_price
    p.is_offer = body.is_offer
    db.commit()
    db.refresh(p)
    return _row_to_out(p)


@router.delete('/{product_id}', status_code=status.HTTP_204_NO_CONTENT)
def clear_offer(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    p = _load_product(db, product_id)
    p.offer_price = None
    p.is_offer = False
    db.commit()

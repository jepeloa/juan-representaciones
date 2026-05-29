from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Product, Supplier, Category, ProductImage, User
from app.schemas import (
    ProductOut, ProductDetailOut, ProductListOut, FacetsOut, SupplierOut, ProductImageOut
)

router = APIRouter(prefix='/api/products', tags=['products'])


def _row_to_out(product: Product) -> ProductOut:
    thumb = product.images[0].src if product.images else None
    return ProductOut(
        id=product.id,
        code=product.code,
        name=product.name,
        description=product.description,
        price=product.price,
        currency=product.currency,
        iva=product.iva,
        supplier_id=product.supplier_id,
        supplier_name=product.supplier.name if product.supplier else '',
        category_id=product.category_id,
        category_name=product.category.name if product.category else None,
        thumbnail=thumb,
    )


@router.get('', response_model=ProductListOut)
def list_products(
    q: str | None = Query(None, description='Búsqueda full-text en nombre/código/descripción'),
    supplier_id: int | None = None,
    category_id: int | None = None,
    currency: str | None = None,
    max_price: Decimal | None = None,
    min_price: Decimal | None = None,
    sort: str = Query('name', pattern='^(name|price|code|supplier|category|-name|-price|-code|-supplier|-category)$'),
    page: int = Query(1, ge=1),
    page_size: int = Query(60, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Product).options(
        selectinload(Product.supplier),
        selectinload(Product.category),
        selectinload(Product.images),
    )
    if supplier_id:
        stmt = stmt.where(Product.supplier_id == supplier_id)
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if currency:
        stmt = stmt.where(Product.currency == currency)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if q:
        pattern = f'%{q.strip()}%'
        stmt = stmt.where(or_(
            Product.name.ilike(pattern),
            Product.code.ilike(pattern),
            Product.description.ilike(pattern),
        ))

    # Sorting
    desc = sort.startswith('-')
    key = sort.lstrip('-')
    sort_map = {
        'name': Product.name,
        'price': Product.price,
        'code': Product.code,
        'supplier': Supplier.name,
        'category': Category.name,
    }
    sort_col = sort_map[key]
    if key in ('supplier', 'category'):
        stmt = stmt.join(Supplier if key == 'supplier' else Category, isouter=True)
    stmt = stmt.order_by(sort_col.desc() if desc else sort_col.asc(), Product.id.asc())

    total = db.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()

    return ProductListOut(
        items=[_row_to_out(p) for p in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get('/facets', response_model=FacetsOut)
def get_facets(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    suppliers_q = (
        select(Supplier, func.count(Product.id).label('cnt'))
        .join(Product, Product.supplier_id == Supplier.id, isouter=True)
        .group_by(Supplier.id)
        .order_by(Supplier.name)
    )
    suppliers = []
    for sup, cnt in db.execute(suppliers_q).all():
        suppliers.append(SupplierOut(id=sup.id, name=sup.name, slug=sup.slug, product_count=cnt))

    currencies = [c for c, in db.execute(
        select(Product.currency).where(Product.currency.is_not(None)).distinct().order_by(Product.currency)
    ).all()]

    min_p, max_p, total = db.execute(
        select(func.min(Product.price), func.max(Product.price), func.count(Product.id))
    ).one()

    return FacetsOut(
        suppliers=suppliers,
        currencies=currencies,
        min_price=min_p,
        max_price=max_p,
        total=total,
    )


@router.get('/{product_id}', response_model=ProductDetailOut)
def get_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    p = db.execute(
        select(Product)
        .options(
            selectinload(Product.supplier),
            selectinload(Product.category),
            selectinload(Product.images),
        )
        .where(Product.id == product_id)
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Producto no encontrado')
    base = _row_to_out(p).model_dump()
    return ProductDetailOut(
        **base,
        unit_per_pack=p.unit_per_pack,
        barcode=p.barcode,
        notes=p.notes,
        source_file=p.source_file,
        images=[ProductImageOut.model_validate(i) for i in p.images],
    )

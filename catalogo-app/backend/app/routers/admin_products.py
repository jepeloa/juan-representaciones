"""Admin CRUD for products, including image upload.

Images live under /srv/uploads/<supplier_slug>/<filename>.jpg on the host (mounted
read-write into the backend). The frontend nginx exposes them under /uploads/.
The DB stores the public URL path (e.g. 'uploads/havard/foo.jpg').
"""
from __future__ import annotations
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from PIL import Image
import io

from app.auth.deps import require_admin
from app.database import get_db
from app.models import Product, ProductImage, Supplier, Category, User
from app.schemas import ProductWriteIn, ProductDetailOut, ProductImageOut
from app.routers.products import _row_to_out

router = APIRouter(prefix='/api/admin/products', tags=['admin-products'])

UPLOAD_ROOT = Path('/srv/uploads')
ALLOWED_IMG_EXT = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_DIM = 600
THUMB_QUALITY = 82


def slugify(s: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', s.lower())
    return s.strip('-') or 'sin-nombre'


def _get_or_create_supplier(db: Session, supplier_id: int | None, supplier_name: str | None) -> Supplier:
    if supplier_id:
        sup = db.get(Supplier, supplier_id)
        if not sup:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f'Proveedor id={supplier_id} no existe')
        return sup
    if not supplier_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Falta supplier_id o supplier_name')
    name = supplier_name.strip()
    sup = db.execute(select(Supplier).where(Supplier.name == name)).scalar_one_or_none()
    if sup:
        return sup
    sup = Supplier(name=name, slug=slugify(name))
    db.add(sup)
    db.flush()
    return sup


def _get_or_create_category(db: Session, supplier_id: int, category_id: int | None, category_name: str | None) -> Category | None:
    if category_id:
        cat = db.get(Category, category_id)
        if cat and cat.supplier_id == supplier_id:
            return cat
        if cat:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'La categoría pertenece a otro proveedor')
    if not category_name:
        return None
    name = category_name.strip()
    cat = db.execute(
        select(Category).where(Category.supplier_id == supplier_id, Category.name == name)
    ).scalar_one_or_none()
    if cat:
        return cat
    cat = Category(supplier_id=supplier_id, name=name)
    db.add(cat)
    db.flush()
    return cat


def _save_image_file(upload: UploadFile, supplier_slug: str) -> str:
    """Validate, resize and save to disk. Returns public src path."""
    suffix = Path(upload.filename or '').suffix.lower()
    if suffix not in ALLOWED_IMG_EXT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f'Formato no permitido: {suffix}. Usar JPG/PNG/WEBP.')
    raw = upload.file.read()
    try:
        img = Image.open(io.BytesIO(raw)).convert('RGB')
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f'No se pudo leer la imagen: {e}')
    img.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
    folder = UPLOAD_ROOT / supplier_slug
    folder.mkdir(parents=True, exist_ok=True)
    fname = f'{uuid.uuid4().hex}.jpg'
    img.save(folder / fname, 'JPEG', quality=THUMB_QUALITY, optimize=True)
    return f'uploads/{supplier_slug}/{fname}'


def _serialize(p: Product) -> ProductDetailOut:
    base = _row_to_out(p).model_dump()
    return ProductDetailOut(
        **base,
        unit_per_pack=p.unit_per_pack,
        barcode=p.barcode,
        notes=p.notes,
        source_file=p.source_file,
        images=[ProductImageOut.model_validate(i) for i in p.images],
    )


@router.post('', response_model=ProductDetailOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    supplier_id: int | None = Form(None),
    supplier_name: str | None = Form(None),
    category_id: int | None = Form(None),
    category_name: str | None = Form(None),
    code: str | None = Form(None),
    name: str = Form(...),
    description: str | None = Form(None),
    price: str | None = Form(None),
    currency: str | None = Form(None),
    iva: str | None = Form(None),
    unit_per_pack: int | None = Form(None),
    barcode: str | None = Form(None),
    notes: str | None = Form(None),
    images: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    sup = _get_or_create_supplier(db, supplier_id, supplier_name)
    cat = _get_or_create_category(db, sup.id, category_id, category_name)
    # Parse price
    parsed_price = None
    if price not in (None, ''):
        try:
            parsed_price = float(price.replace(',', '.'))
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f'Precio inválido: {price}')
    product = Product(
        supplier_id=sup.id,
        category_id=cat.id if cat else None,
        code=(code.strip() if code else None),
        name=name.strip()[:500],
        description=description or None,
        price=parsed_price,
        currency=(currency or None),
        iva=(iva or None),
        unit_per_pack=unit_per_pack,
        barcode=(barcode.strip()[:60] if barcode else None),
        notes=(notes or None),
        source_file='manual',
    )
    db.add(product)
    db.flush()
    # Attach images
    for pos, upload in enumerate(images or []):
        if not upload or not upload.filename:
            continue
        src = _save_image_file(upload, sup.slug)
        db.add(ProductImage(product_id=product.id, src=src, position=pos))
    db.commit()
    db.refresh(product)
    # Eager load
    product = db.execute(
        select(Product).options(
            selectinload(Product.supplier),
            selectinload(Product.category),
            selectinload(Product.images),
        ).where(Product.id == product.id)
    ).scalar_one()
    return _serialize(product)


@router.patch('/{product_id}', response_model=ProductDetailOut)
async def update_product(
    product_id: int,
    supplier_id: int | None = Form(None),
    supplier_name: str | None = Form(None),
    category_id: int | None = Form(None),
    category_name: str | None = Form(None),
    code: str | None = Form(None),
    name: str | None = Form(None),
    description: str | None = Form(None),
    price: str | None = Form(None),
    currency: str | None = Form(None),
    iva: str | None = Form(None),
    unit_per_pack: int | None = Form(None),
    barcode: str | None = Form(None),
    notes: str | None = Form(None),
    images: list[UploadFile] = File(default=[]),
    clear_images: bool = Form(False),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    product = db.execute(
        select(Product).options(
            selectinload(Product.supplier),
            selectinload(Product.images),
        ).where(Product.id == product_id)
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Producto no encontrado')

    if supplier_id or supplier_name:
        sup = _get_or_create_supplier(db, supplier_id, supplier_name)
        product.supplier_id = sup.id
    if category_id or category_name:
        cat = _get_or_create_category(db, product.supplier_id, category_id, category_name)
        product.category_id = cat.id if cat else None
    if code is not None:
        product.code = code.strip() or None
    if name is not None:
        product.name = name.strip()[:500]
    if description is not None:
        product.description = description or None
    if price is not None:
        if price == '':
            product.price = None
        else:
            try:
                product.price = float(price.replace(',', '.'))
            except ValueError:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f'Precio inválido: {price}')
    if currency is not None:
        product.currency = currency or None
    if iva is not None:
        product.iva = iva or None
    if unit_per_pack is not None:
        product.unit_per_pack = unit_per_pack
    if barcode is not None:
        product.barcode = (barcode.strip()[:60]) or None
    if notes is not None:
        product.notes = notes or None

    if clear_images:
        for im in list(product.images):
            db.delete(im)
        db.flush()

    sup = db.get(Supplier, product.supplier_id)
    for pos, upload in enumerate(images or []):
        if not upload or not upload.filename:
            continue
        src = _save_image_file(upload, sup.slug)
        db.add(ProductImage(product_id=product.id, src=src, position=len(product.images) + pos))

    db.commit()
    product = db.execute(
        select(Product).options(
            selectinload(Product.supplier),
            selectinload(Product.category),
            selectinload(Product.images),
        ).where(Product.id == product.id)
    ).scalar_one()
    return _serialize(product)


@router.delete('/{product_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Producto no encontrado')
    db.delete(product)
    db.commit()

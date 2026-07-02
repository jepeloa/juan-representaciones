from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Category, Product, User
from app.schemas import CategoryOut

router = APIRouter(prefix='/api/categories', tags=['categories'])


@router.get('', response_model=list[CategoryOut])
def list_categories(
    supplier_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Deduplicado por NOMBRE: la misma categoría existe por proveedor, pero en el
    # filtro debe aparecer una sola vez y traer productos de todas las marcas.
    # Cliente: contar solo productos habilitados.
    prod_join = Product.category_id == Category.id
    if not user.is_admin:
        prod_join = and_(prod_join, Product.is_active.is_(True))
    q = (
        select(
            Category.name.label('name'),
            func.count(Product.id).label('cnt'),
            func.min(Category.id).label('id'),
        )
        .join(Product, prod_join, isouter=True)
        .group_by(Category.name)
        .order_by(Category.name)
    )
    if supplier_id:
        q = q.where(Category.supplier_id == supplier_id)
    return [
        CategoryOut(id=row.id, name=row.name, supplier_id=supplier_id or 0, product_count=row.cnt)
        for row in db.execute(q).all()
    ]

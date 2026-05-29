from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
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
    _: User = Depends(get_current_user),
):
    q = (
        select(Category, func.count(Product.id).label('cnt'))
        .join(Product, Product.category_id == Category.id, isouter=True)
        .group_by(Category.id)
        .order_by(Category.name)
    )
    if supplier_id:
        q = q.where(Category.supplier_id == supplier_id)
    return [
        CategoryOut(id=c.id, name=c.name, supplier_id=c.supplier_id, product_count=cnt)
        for c, cnt in db.execute(q).all()
    ]

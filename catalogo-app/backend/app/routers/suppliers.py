from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Supplier, Product, User
from app.schemas import SupplierOut, PaymentConditionBrief

router = APIRouter(prefix='/api/suppliers', tags=['suppliers'])


@router.get('', response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Cliente: solo marcas habilitadas y contando solo productos habilitados.
    # Admin: todas, con el flag is_active para poder reactivarlas.
    prod_join = Product.supplier_id == Supplier.id
    if not user.is_admin:
        prod_join = and_(prod_join, Product.is_active.is_(True))
    q = (
        select(Supplier, func.count(Product.id).label('cnt'))
        .join(Product, prod_join, isouter=True)
        .group_by(Supplier.id)
        .order_by(Supplier.sort_order.is_(None), Supplier.sort_order.asc(), Supplier.name)
    )
    if not user.is_admin:
        q = q.where(Supplier.is_active.is_(True))
    return [
        SupplierOut(
            id=s.id, name=s.name, slug=s.slug, image=s.image, product_count=cnt, is_active=s.is_active,
            payment_conditions=[
                PaymentConditionBrief(id=c.id, name=c.name, description=c.description)
                for c in s.payment_conditions if c.is_active
            ],
        )
        for s, cnt in db.execute(q).all()
    ]

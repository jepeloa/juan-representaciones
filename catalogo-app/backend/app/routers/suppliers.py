from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Supplier, Product, User
from app.schemas import SupplierOut, PaymentConditionBrief

router = APIRouter(prefix='/api/suppliers', tags=['suppliers'])


@router.get('', response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    q = (
        select(Supplier, func.count(Product.id).label('cnt'))
        .join(Product, Product.supplier_id == Supplier.id, isouter=True)
        .group_by(Supplier.id)
        .order_by(Supplier.name)
    )
    return [
        SupplierOut(
            id=s.id, name=s.name, slug=s.slug, image=s.image, product_count=cnt,
            payment_conditions=[
                PaymentConditionBrief(id=c.id, name=c.name, description=c.description)
                for c in s.payment_conditions if c.is_active
            ],
        )
        for s, cnt in db.execute(q).all()
    ]

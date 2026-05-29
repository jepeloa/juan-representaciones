from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    __tablename__ = 'categories'
    __table_args__ = (UniqueConstraint('supplier_id', 'name', name='uq_supplier_category'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(255))

    supplier: Mapped['Supplier'] = relationship()  # noqa: F821
    products: Mapped[list['Product']] = relationship(back_populates='category')  # noqa: F821

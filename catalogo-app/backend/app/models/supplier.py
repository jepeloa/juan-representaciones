from sqlalchemy import String, Integer, Boolean, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Condiciones de pago por MARCA (N-a-N)
supplier_payment_conditions = Table(
    'supplier_payment_conditions',
    Base.metadata,
    Column('supplier_id', ForeignKey('suppliers.id', ondelete='CASCADE'), primary_key=True),
    Column('payment_condition_id', ForeignKey('payment_conditions.id', ondelete='CASCADE'), primary_key=True),
)


class Supplier(Base):
    __tablename__ = 'suppliers'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    # Foto/logo de la marca (ruta pública, ej. 'uploads/brands/xxx.jpg')
    image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Orden de destacado de la marca (NULL = sin destacar). Menor = primero.
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Marca habilitada. Si es False, no se muestra al cliente (ni sus productos).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='1', index=True)

    products: Mapped[list['Product']] = relationship(back_populates='supplier')  # noqa: F821
    payment_conditions: Mapped[list['PaymentCondition']] = relationship(  # noqa: F821
        secondary=supplier_payment_conditions, lazy='selectin',
        order_by='PaymentCondition.sort_order', back_populates='suppliers',
    )

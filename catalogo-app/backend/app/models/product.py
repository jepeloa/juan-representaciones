from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, Numeric, Integer, Boolean, Index, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Asociación N-a-N: un producto puede tener varias condiciones de pago
product_payment_conditions = Table(
    'product_payment_conditions',
    Base.metadata,
    Column('product_id', ForeignKey('products.id', ondelete='CASCADE'), primary_key=True),
    Column('payment_condition_id', ForeignKey('payment_conditions.id', ondelete='CASCADE'), primary_key=True),
)


class Product(Base):
    __tablename__ = 'products'
    __table_args__ = (
        Index('ix_products_supplier_category', 'supplier_id', 'category_id'),
        Index('ix_products_search', 'name', 'code'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id', ondelete='CASCADE'), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)

    code: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True, index=True)
    # Oferta: precio rebajado fijo + interruptor manual. Está "en oferta" cuando
    # is_offer es True y offer_price no es None.
    offer_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    is_offer: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0', index=True)
    # Orden de destacados (NULL = no destacado). Menor = aparece primero.
    # Separado por sección: catálogo y ofertas.
    catalog_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offer_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    iva: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unit_per_pack: Mapped[int | None] = mapped_column(Integer, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Producto habilitado. Si es False, no se muestra al cliente.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='1', index=True)

    supplier: Mapped['Supplier'] = relationship(back_populates='products')  # noqa: F821
    category: Mapped['Category | None'] = relationship(back_populates='products')  # noqa: F821
    payment_conditions: Mapped[list['PaymentCondition']] = relationship(  # noqa: F821
        secondary=product_payment_conditions, lazy='selectin', order_by='PaymentCondition.sort_order',
    )
    images: Mapped[list['ProductImage']] = relationship(
        back_populates='product', cascade='all, delete-orphan', order_by='ProductImage.position'
    )


class ProductImage(Base):
    __tablename__ = 'product_images'

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), index=True)
    src: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates='images')

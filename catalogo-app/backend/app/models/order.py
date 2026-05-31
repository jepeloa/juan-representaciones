from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    payment_condition_id: Mapped[int | None] = mapped_column(
        ForeignKey('payment_conditions.id', ondelete='SET NULL'), nullable=True
    )

    # Snapshot of payment condition at creation time (so PDF stays correct
    # even if condition is edited/deleted later)
    payment_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_multiplier: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal('1.0000'))

    # Currency totals computed by aggregating items (ARS only — USD items show separately)
    subtotal_ars: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal('0.00'))
    total_ars: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal('0.00'))
    subtotal_usd: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal('0.00'))
    total_usd: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal('0.00'))

    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='draft')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Email tracking
    email_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_status: Mapped[str] = mapped_column(String(20), default='pending')  # pending|sent|failed|disabled
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list['OrderItem']] = relationship(
        back_populates='order', cascade='all, delete-orphan', order_by='OrderItem.id'
    )


class OrderItem(Base):
    __tablename__ = 'order_items'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id', ondelete='CASCADE'), index=True)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey('products.id', ondelete='SET NULL'), nullable=True
    )

    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_list: Mapped[Decimal] = mapped_column(Numeric(14, 2))  # price at the time of ordering
    unit_price_final: Mapped[Decimal] = mapped_column(Numeric(14, 2))  # list * multiplier
    currency: Mapped[str] = mapped_column(String(8))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    # Snapshot
    product_name: Mapped[str] = mapped_column(String(500))
    product_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_term: Mapped[str | None] = mapped_column(String(500), nullable=True)

    order: Mapped[Order] = relationship(back_populates='items')

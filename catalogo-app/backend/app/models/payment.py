from decimal import Decimal
from sqlalchemy import String, Boolean, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentCondition(Base):
    """Payment terms with a price multiplier.

    Examples:
        Contado          -> multiplier 0.95 (5% off)
        Cheque 30 días   -> multiplier 1.00 (price list)
        Cheque 60 días   -> multiplier 1.08
        Cheque 90 días   -> multiplier 1.15
    """
    __tablename__ = 'payment_conditions'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    multiplier: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal('1.0000'))
    days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

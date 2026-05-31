from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaymentTerm(Base):
    """Condición de pago en texto libre, asociada (opcionalmente) a un proveedor.

    Distinta de PaymentCondition (que aplica un multiplicador en el checkout):
    esto es un texto informativo que se asigna por producto y se muestra
    agrupado en la orden. Ej.: "30% anticipo, saldo contra entrega".
    """
    __tablename__ = 'payment_terms'

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(500))
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    supplier: Mapped['Supplier | None'] = relationship()  # noqa: F821

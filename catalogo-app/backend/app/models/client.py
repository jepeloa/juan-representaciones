from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClientProfile(Base):
    """Datos comerciales/de facturación de un cliente. Todos opcionales.

    Se carga/edita desde el panel de admin (sección Clientes).
    """
    __tablename__ = 'client_profiles'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True
    )

    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)   # Razón social
    tax_id: Mapped[str | None] = mapped_column(String(40), nullable=True)          # CUIT / CUIL
    tax_condition: Mapped[str | None] = mapped_column(String(60), nullable=True)   # Condición IVA
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    address_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ActivityEvent(Base):
    """Evento de actividad de un usuario en la plataforma (analytics).

    event_type: login | page_view | product_view | add_to_cart |
                view_conditions | view_stock | search | order
    """
    __tablename__ = 'activity_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)   # nombre de producto, texto buscado, etc.
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)    # ruta del front
    ref_id: Mapped[int | None] = mapped_column(nullable=True)               # id de producto/marca relacionado
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

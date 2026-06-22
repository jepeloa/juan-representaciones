from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.orders import OrderOut


# ===== Perfil del cliente (admin) =====

class ClientProfileIn(BaseModel):
    company_name: str | None = None
    tax_id: str | None = None
    tax_condition: str | None = None
    email: str | None = None
    phone: str | None = None
    contact_name: str | None = None
    address_street: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_zip: str | None = None
    notes: str | None = None


class ClientProfileOut(ClientProfileIn):
    id: int
    user_id: int
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ===== Actividad =====

class ActivityEventIn(BaseModel):
    event_type: str
    label: str | None = None
    path: str | None = None
    ref_id: int | None = None


class ActivityEventOut(BaseModel):
    id: int
    event_type: str
    label: str | None = None
    path: str | None = None
    ref_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Listado y detalle de clientes (admin) =====

class ClientListItemOut(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    is_active: bool
    created_at: datetime
    company_name: str | None = None
    visits: int = 0            # cantidad de inicios de sesión
    events_count: int = 0      # total de eventos registrados
    orders_count: int = 0
    total_ars: Decimal = Decimal('0.00')
    total_usd: Decimal = Decimal('0.00')
    last_active: datetime | None = None


class ActivityCount(BaseModel):
    event_type: str
    count: int


class TopProduct(BaseModel):
    ref_id: int | None = None
    label: str | None = None
    count: int


class ClientStatsOut(BaseModel):
    visits: int = 0
    events_count: int = 0
    orders_count: int = 0
    total_ars: Decimal = Decimal('0.00')
    total_usd: Decimal = Decimal('0.00')
    first_active: datetime | None = None
    last_active: datetime | None = None
    by_type: list[ActivityCount] = []
    top_products: list[TopProduct] = []


class ClientDetailOut(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    profile: ClientProfileOut | None = None
    stats: ClientStatsOut
    recent_activity: list[ActivityEventOut] = []
    orders: list[OrderOut] = []

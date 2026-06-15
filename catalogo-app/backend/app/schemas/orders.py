from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class PaymentConditionIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    multiplier: Decimal = Decimal('1.0000')
    days: int | None = None
    is_active: bool = True
    sort_order: int = 0
    supplier_ids: list[int] = []  # marcas a las que aplica


class PaymentConditionOut(BaseModel):
    id: int
    name: str
    description: str | None
    multiplier: Decimal
    days: int | None
    is_active: bool
    sort_order: int
    supplier_ids: list[int] = []

    class Config:
        from_attributes = True


class SettingIn(BaseModel):
    key: str = Field(min_length=1, max_length=60)
    value: str | None = None


class SettingsBulkIn(BaseModel):
    settings: dict[str, str | None]


class SettingsOut(BaseModel):
    catalog_disclaimer: str | None = None
    catalog_terms: str | None = None
    company_name: str | None = None
    company_contact: str | None = None
    order_notification_email: str | None = None


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=999)


class OrderCreateIn(BaseModel):
    payment_condition_id: int | None = None
    customer_notes: str | None = None
    items: list[OrderItemIn]


class OrderItemOut(BaseModel):
    id: int
    product_id: int | None
    quantity: int
    unit_price_list: Decimal
    unit_price_final: Decimal
    currency: str
    line_total: Decimal
    product_name: str
    product_code: str | None
    supplier_name: str | None
    payment_term: str | None = None

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    user_id: int | None
    payment_condition_id: int | None
    payment_name: str | None
    payment_multiplier: Decimal
    subtotal_ars: Decimal
    total_ars: Decimal
    subtotal_usd: Decimal
    total_usd: Decimal
    customer_notes: str | None
    status: str
    created_at: datetime
    email_to: str | None = None
    email_status: str = 'pending'
    email_sent_at: datetime | None = None
    email_error: str | None = None
    items: list[OrderItemOut]

    class Config:
        from_attributes = True

from decimal import Decimal
from pydantic import BaseModel, Field


# ===== Users =====
class UserCreateIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=128)
    full_name: str | None = None
    is_admin: bool = False
    is_active: bool = True


class UserUpdateIn(BaseModel):
    full_name: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=4, max_length=128)


class UserAdminOut(BaseModel):
    id: int
    username: str
    full_name: str | None
    is_admin: bool
    is_active: bool

    class Config:
        from_attributes = True


# ===== Products =====
class ProductWriteIn(BaseModel):
    supplier_id: int | None = None
    supplier_name: str | None = None  # if provided and supplier_id is None, create/find
    category_id: int | None = None
    category_name: str | None = None  # if provided and category_id is None, create/find under supplier
    code: str | None = None
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    price: Decimal | None = None
    currency: str | None = Field(default=None, max_length=8)
    iva: str | None = Field(default=None, max_length=40)
    unit_per_pack: int | None = None
    barcode: str | None = Field(default=None, max_length=60)
    notes: str | None = None
